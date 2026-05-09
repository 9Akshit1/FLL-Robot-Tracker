"""
Converts recorded robot CSV motor logs into SPIKE Prime MicroPython replay scripts.
Generates both an exact frame-by-frame timeline replay and a simplified semantic segment-based replay.

ICS4U
May 7, 2026
"""

import json
import csv
from pathlib import Path

MOTOR_CALIBRATION = {
    'A': {'multiplier': 2.14, 'min_speed': 20, 'max_speed': 750},
    'B': {'multiplier': 2.14, 'min_speed': 20, 'max_speed': 750},
    'C': {'multiplier': 2.14, 'min_speed': 10, 'max_speed': 750},
}

def parse_motor_columns(csv_headers):
    """
    Detects motor relative position columns in a CSV header list and maps them to motor ports.
    This allows the converter to automatically determine which motors were recorded.

    Args:
        csv_headers (list[str]): List of CSV column header strings.

    Returns:
        dict: Dictionary mapping motor ports to detected CSV column keys.
    """
    motors_found = {}
    for header in csv_headers:
        header_clean = header.replace('\ufeff', '').strip()
        for port in ['A', 'B', 'C', 'D', 'E', 'F']:
            if f'motor{port}_rel_deg' in header_clean:
                if port not in motors_found:
                    motors_found[port] = {}
                motors_found[port]['rel_key'] = header_clean
                print(f"[CONVERT] Found {port} relative: {header_clean}")
    return motors_found


def extract_motor_data(csv_path):
    """
    Reads all rows from a recorded CSV file and converts them into frame dictionaries with motor deltas.
    Each frame includes time, motor positions, and change in motor position since the previous frame.

    Args:
        csv_path (str): Path to the input CSV file.

    Returns:
        tuple[list[dict], dict]: A list of frame dictionaries and a motor column mapping dictionary.
    """
    frames = []
    motor_columns = None

    print(f"[CONVERT] Opening CSV: {csv_path}")

    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)

            if reader.fieldnames:
                cleaned_fieldnames = [n.replace('\ufeff', '').strip() for n in reader.fieldnames]
                motor_columns = parse_motor_columns(cleaned_fieldnames)
                print(f"[CONVERT] Motors detected: {list(motor_columns.keys())}")

                if not motor_columns:
                    return [], {}

            prev_motors = {port: 0.0 for port in motor_columns.keys()}

            for row in reader:
                try:
                    time_ms = int(float(row.get('time_ms', 0)))
                    current_motors = {}

                    for port, keys in motor_columns.items():
                        rel_key = keys.get('rel_key')
                        if rel_key and rel_key in row:
                            try:
                                current_motors[port] = float(row[rel_key])
                            except Exception:
                                current_motors[port] = 0.0

                    frame_deltas = {
                        port: current_motors[port] - prev_motors[port]
                        for port in current_motors
                    }

                    frames.append({
                        'time_ms': time_ms,
                        'motors': current_motors,
                        'deltas': frame_deltas
                    })

                    prev_motors = current_motors.copy()

                except Exception:
                    continue

        print(f"[CONVERT] Extracted {len(frames)} frames from CSV")
        if frames:
            print(f"[CONVERT] Frame time range: {frames[0]['time_ms']}ms to {frames[-1]['time_ms']}ms")

        return frames, motor_columns

    except Exception as e:
        print(f"[CONVERT] ERROR parsing CSV: {e}")
        raise

def calculate_speed(motor_port, delta_degrees, dt_ms):
    """
    Converts a recorded motor delta into an estimated SPIKE Prime speed value using calibration constants.
    Output is clamped to valid SPIKE speed ranges for the motor.

    Args:
        motor_port (str): Motor port letter (A-F).
        delta_degrees (float): Change in motor position in degrees.
        dt_ms (int): Time interval between frames in milliseconds.

    Returns:
        int: Speed value between 0 and 750 for SPIKE motor commands.
    """
    if dt_ms <= 0:
        dt_ms = 30
    if abs(delta_degrees) < 0.5:
        return 0

    calib = MOTOR_CALIBRATION.get(motor_port, {'multiplier': 2.14, 'min_speed': 20, 'max_speed': 750})
    deg_per_sec = abs(delta_degrees) / (dt_ms / 1000.0)
    speed = int(deg_per_sec * calib['multiplier'])
    speed = max(calib['min_speed'], min(calib['max_speed'], speed))
    return speed

def build_timeline(frames):
    """
    Converts frame data into a timeline of replay commands that preserve exact recorded timing.
    Each timeline entry stores the delay and motor movement commands for that interval.

    Args:
        frames (list[dict]): List of frame dictionaries produced from the CSV.

    Returns:
        list[dict]: Timeline list containing delay values and motor movement commands.
    """
    timeline = []

    for i in range(len(frames) - 1):
        curr = frames[i]
        nxt  = frames[i + 1]

        dt_ms = nxt['time_ms'] - curr['time_ms']
        if dt_ms <= 0:
            dt_ms = 30

        motor_commands = {}
        for port in sorted(nxt['deltas'].keys()):
            delta = nxt['deltas'][port]
            if abs(delta) >= 0.5:
                speed = calculate_speed(port, delta, dt_ms)
                if speed > 0:
                    motor_commands[port] = [int(round(delta)), speed]

        # Always append so timing gaps (idle frames) are preserved too
        timeline.append({
            'delay_ms': dt_ms,
            'motors': motor_commands
        })

    total_ms = sum(e['delay_ms'] for e in timeline)
    active   = sum(1 for e in timeline if e['motors'])
    print(f"[CONVERT] Built timeline: {len(timeline)} frames, {active} with motor movement, {total_ms}ms total")
    return timeline


def generate_timeline_script(timeline, motor_columns):
    """
    Builds a SPIKE Prime MicroPython script that replays movement using frame-by-frame timeline data.
    Motor commands are executed in parallel and then delayed to match recorded timing.

    Args:
        timeline (list[dict]): Timeline entries containing delays and motor commands.
        motor_columns (dict): Mapping of detected motor ports from the CSV header.

    Returns:
        str: Complete MicroPython script text for exact replay.
    """
    all_motors = sorted(motor_columns.keys())
    port_lines = "".join(f'    "{p}": port.{p},\n' for p in all_motors)
    total_ms   = sum(e['delay_ms'] for e in timeline)

    script = f"""\
import motor
import runloop
from hub import port

PORT_MAP = {{
{port_lines}}}

# {len(timeline)} frames, ~{total_ms}ms total recorded time
# Each entry: {{'delay_ms': int, 'motors': {{'A': [degrees, speed], ...}}}}
TIMELINE = {repr(timeline)}

async def main():
    print("FLL Timeline Replay")
    print(str(len(TIMELINE)) + " frames / {total_ms}ms")

    for idx, frame in enumerate(TIMELINE):
        dt   = frame['delay_ms']
        cmds = frame['motors']

        # Fire all motors for this frame simultaneously (non-blocking)
        for port_name, cmd in cmds.items():
            if port_name in PORT_MAP:
                target_deg = cmd[0]
                speed      = cmd[1]
                if target_deg != 0:
                    motor.run_for_degrees(PORT_MAP[port_name], target_deg, speed)

        # Wait the exact recorded inter-frame interval
        # Motors started above keep running during this sleep -- correct behaviour,
        # as it mirrors how the robot moved during recording.
        if dt > 0:
            await runloop.sleep_ms(dt)

        if (idx + 1) % 20 == 0:
            print("frame " + str(idx + 1) + "/" + str(len(TIMELINE)))

    # Let any still-running motors finish
    await runloop.sleep_ms(300)
    print("Done!")

runloop.run(main())
"""
    return script


# Maps movement_analysis description keywords -> which motors, base speed, direction
SEMANTIC_MOTOR_MAP = {
    'drive forward':  {'A': (400, -1), 'B': (400, -1)},
    'drive backward': {'A': (400, +1), 'B': (400, +1)},
    'turn left':      {'A': (300, +1), 'B': (300, -1)},
    'turn right':     {'A': (300, -1), 'B': (300, +1)},
    'raise arm':      {'C': (200, +1)},
    'lower arm':      {'C': (200, -1)},
}


def parse_segment_motors(description):
    """
    Matches a segment description against known movement keywords to determine motor commands.
    Multiple actions can be combined in one description string.

    Args:
        description (str): Segment description text such as "Drive Forward + Raise Arm".

    Returns:
        dict: Dictionary mapping motor ports to (speed, direction_sign) tuples.
    """
    desc_lower = description.lower()
    combined = {}
    for keyword, motor_map in SEMANTIC_MOTOR_MAP.items():
        if keyword in desc_lower:
            for port, (speed, sign) in motor_map.items():
                combined[port] = (speed, sign)
    return combined


def degrees_for_duration(speed_val, duration_ms, calib_multiplier=2.14):
    """
    Matches a segment description against known movement keywords to determine motor commands.
    Multiple actions can be combined in one description string.

    Args:
        description (str): Segment description text such as "Drive Forward + Raise Arm".

    Returns:
        dict: Dictionary mapping motor ports to (speed, direction_sign) tuples.
    """
    deg_per_sec = speed_val / calib_multiplier
    return int(deg_per_sec * (duration_ms / 1000.0))


def generate_display_script(segments_data, motor_columns):
    """
    Generates a simplified semantic replay script using labeled movement segments.
    Unknown segments are treated as idle delays to preserve total run time.

    Args:
        segments_data (list[dict]): List of segment dictionaries containing descriptions and durations.
        motor_columns (dict): Mapping of detected motor ports from the CSV header.

    Returns:
        str: Complete MicroPython script text for semantic replay.
    """
    all_motors = sorted(motor_columns.keys())
    port_lines = "".join(f'    "{p}": port.{p},\n' for p in all_motors)

    # Build segment command list
    seg_commands = []
    if segments_data:
        for seg in segments_data:
            desc     = seg.get('description', 'Idle')
            duration = int(seg.get('duration_ms', 0))

            if duration <= 0:
                continue

            if 'idle' in desc.lower():
                seg_commands.append({
                    'desc': 'Idle',
                    'duration_ms': duration,
                    'motors': {}
                })
                continue

            motor_cmds_raw = parse_segment_motors(desc)
            if not motor_cmds_raw:
                # Unknown label -- pause to preserve timing
                seg_commands.append({'desc': desc, 'duration_ms': duration, 'motors': {}})
                continue

            motor_degrees = {}
            for port, (speed, sign) in motor_cmds_raw.items():
                calib = MOTOR_CALIBRATION.get(port, {'multiplier': 2.14})
                deg = degrees_for_duration(speed, duration, calib['multiplier'])
                motor_degrees[port] = [deg * sign, speed]

            seg_commands.append({
                'desc': desc,
                'duration_ms': duration,
                'motors': motor_degrees
            })

    total_ms = sum(s['duration_ms'] for s in seg_commands)

    script = f"""\
import motor
import runloop
from hub import port

PORT_MAP = {{
{port_lines}}}

# Semantic segment replay -- {len(seg_commands)} segments, ~{total_ms}ms total
# Each entry: {{'desc': str, 'duration_ms': int, 'motors': {{'A': [degrees, speed], ...}}}}
SEGMENTS = {repr(seg_commands)}

async def main():
    print("FLL Semantic Replay")
    print(str(len(SEGMENTS)) + " segments / {total_ms}ms")

    for seg in SEGMENTS:
        desc     = seg['desc']
        duration = seg['duration_ms']
        cmds     = seg['motors']

        print(">> " + desc + " (" + str(duration) + "ms)")

        # Fire all motors for this segment simultaneously
        for port_name, cmd in cmds.items():
            if port_name in PORT_MAP:
                target_deg = cmd[0]
                speed      = cmd[1]
                if target_deg != 0:
                    motor.run_for_degrees(PORT_MAP[port_name], target_deg, speed)

        # Hold for the full segment duration so timing matches the recording
        if duration > 0:
            await runloop.sleep_ms(duration)

    await runloop.sleep_ms(300)
    print("Done!")

runloop.run(main())
"""
    return script

def generate_spike_script(csv_path, out_path_timeline, out_path_display, config=None):
    """
    Converts a recorded CSV into both a timeline replay script and a semantic display replay script.
    Output scripts are written to the provided output file paths.

    Args:
        csv_path (str): Path to the recorded CSV file.
        out_path_timeline (str): Output path for the generated timeline replay script.
        out_path_display (str): Output path for the generated semantic replay script.
        config (dict | None): Optional configuration dictionary (currently unused).

    Returns:
        tuple[str, str]: Generated timeline script text and display script text.
    """
    csv_path          = Path(csv_path)
    out_path_timeline = Path(out_path_timeline)
    out_path_display  = Path(out_path_display)
    segments_json     = csv_path.parent / "segments.json"

    print(f"\n[CONVERT] Starting conversion...")
    print(f"[CONVERT] Input: {csv_path}")

    try:
        frames, motor_columns = extract_motor_data(str(csv_path))

        if not frames:
            raise ValueError("Failed to extract frames from CSV")

        # Load segments if available
        segments_data = None
        if segments_json.exists():
            print(f"[CONVERT] Loading segments from {segments_json}")
            with open(segments_json, 'r') as f:
                segments_data = json.load(f)
            print(f"[CONVERT] Loaded {len(segments_data)} segments")
        else:
            print(f"[CONVERT] No segments.json at {segments_json} -- display script will be minimal")

        # Timeline script
        print(f"\n[CONVERT] Building frame-by-frame timeline...")
        timeline = build_timeline(frames)

        print(f"\n[CONVERT] Generating timeline script...")
        timeline_script = generate_timeline_script(timeline, motor_columns)

        # Display script
        print(f"[CONVERT] Generating semantic display script...")
        display_script = generate_display_script(segments_data or [], motor_columns)

        # Write files
        out_path_timeline.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path_timeline, 'w', encoding='utf-8') as f:
            f.write(timeline_script)
        print(f"[CONVERT] Timeline script: {len(timeline_script)} bytes -> {out_path_timeline}")

        out_path_display.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path_display, 'w', encoding='utf-8') as f:
            f.write(display_script)
        print(f"[CONVERT] Display script:  {len(display_script)} bytes -> {out_path_display}")

        # Debug print timeline (only active frames to keep logs short)
        print(f"\n[CONVERT] ===== TIMELINE SUMMARY ({len(timeline)} frames) =====")
        total_time = 0
        for idx, entry in enumerate(timeline):
            total_time += entry['delay_ms']
            if entry['motors']:
                parts = [f"{p}:({cmd[0]:+d}deg@{cmd[1]})" for p, cmd in entry['motors'].items()]
                print(f"[CONVERT] [{idx:3d}] {entry['delay_ms']:3d}ms | {' '.join(parts)}")
        print(f"[CONVERT] ===== TOTAL TIME: {total_time}ms =====\n")

        print(f"[CONVERT] Conversion complete\n")
        return timeline_script, display_script

    except Exception as e:
        print(f"[CONVERT] ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    csv_path     = Path("backend/data/raw_data.csv")
    out_timeline = Path("backend/data/generated_spike.py")
    out_display  = Path("backend/data/generated_spike_display.py")
    generate_spike_script(str(csv_path), str(out_timeline), str(out_display))
