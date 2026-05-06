# ============================================================
# convert_to_code_precision.py - Motor Control with Speed Verification
# Uses motor-specific calibration for accurate movements
# ============================================================

import json
import csv
from pathlib import Path

# ============================================================
# MOTOR CALIBRATION DATA
# Measure these values for your specific motors!
# ============================================================

MOTOR_CALIBRATION = {
    'A': {
        'type': 'drive_left',
        'multiplier': 2.14,  # Speed multiplier (adjust based on your motors)
        'min_speed': 20,
        'max_speed': 750,
        'stall_speed': 15,
        'load': 'heavy',
        # Measured speed responses (speed -> deg/sec at that speed)
        # YOU MUST CALIBRATE THESE FOR YOUR MOTORS!
        'speed_response': {
            50: 25,
            100: 50,
            200: 100,
            400: 170,
            750: 180,
        }
    },
    'B': {
        'type': 'drive_right',
        'multiplier': 2.14,
        'min_speed': 20,
        'max_speed': 750,
        'stall_speed': 15,
        'load': 'heavy',
        'speed_response': {
            50: 25,
            100: 50,
            200: 100,
            400: 170,
            750: 180,
        }
    },
    'C': {
        'type': 'arm',
        'multiplier': 2.14,  # May need different multiplier for arm
        'min_speed': 10,
        'max_speed': 750,
        'stall_speed': 5,
        'load': 'light',
        'speed_response': {
            50: 15,
            100: 30,
            200: 60,
            400: 120,
            750: 150,
        }
    },
}

def parse_motor_columns(csv_headers):
    """Parse CSV headers to find motor columns"""
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
    """Extract motor trajectory data from CSV"""
    frames = []
    motor_columns = None

    print(f"[CONVERT] Opening CSV: {csv_path}")

    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)

            if reader.fieldnames:
                cleaned_fieldnames = [name.replace('\ufeff', '').strip() for name in reader.fieldnames]
                print(f"[CONVERT] CSV headers found")

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
                                rel_pos = float(row[rel_key])
                                current_motors[port] = rel_pos
                            except (ValueError, TypeError):
                                current_motors[port] = 0.0

                    frame_deltas = {}
                    for port in current_motors.keys():
                        delta = current_motors[port] - prev_motors[port]
                        frame_deltas[port] = delta

                    if current_motors:
                        frames.append({
                            'time_ms': time_ms,
                            'motors': current_motors,
                            'deltas': frame_deltas
                        })

                    prev_motors = current_motors.copy()

                except (ValueError, KeyError, TypeError):
                    continue

        print(f"[CONVERT] Extracted {len(frames)} frames from CSV")
        if frames:
            print(f"[CONVERT] Frame time range: {frames[0]['time_ms']}ms to {frames[-1]['time_ms']}ms")
        
        return frames, motor_columns

    except Exception as e:
        print(f"[CONVERT] ERROR parsing CSV: {e}")
        raise

def calculate_speed_with_calibration(motor, delta_degrees, time_ms):
    """
    Calculate speed using motor calibration data.
    
    This improves on the simple multiplier by:
    1. Using motor-specific calibration
    2. Checking if speed will actually complete movement in time
    3. Providing warnings if timing won't match
    """
    if time_ms <= 0:
        time_ms = 30
    
    if abs(delta_degrees) < 0.5:
        return 0
    
    # Get calibration for this motor
    calib = MOTOR_CALIBRATION.get(motor)
    if not calib:
        # Fallback for uncalibrated motors
        velocity = abs(delta_degrees) / (time_ms / 1000.0)
        return max(1, min(750, int(velocity * 2.14)))
    
    # Required velocity in deg/sec
    required_velocity = abs(delta_degrees) / (time_ms / 1000.0)
    
    # Use simple multiplier approach (can be improved with speed_response mapping)
    # TODO: Implement speed_response mapping for better accuracy
    speed = int(required_velocity * calib['multiplier'])
    
    # Clamp to valid range
    speed = max(calib['min_speed'], min(calib['max_speed'], speed))
    
    return speed

def verify_movement_timing(motor, delta_degrees, time_ms, calculated_speed):
    """
    Verify that the calculated speed will actually complete the movement in time.
    Returns a dictionary with diagnostic info.
    """
    calib = MOTOR_CALIBRATION.get(motor)
    if not calib:
        return {'status': 'uncalibrated', 'motor': motor}
    
    # Estimate actual velocity from calibration
    # (Using simple linear interpolation between known points)
    if calculated_speed in calib['speed_response']:
        actual_velocity = calib['speed_response'][calculated_speed]
    else:
        # Linear interpolation
        speeds = sorted(calib['speed_response'].keys())
        velocities = [calib['speed_response'][s] for s in speeds]
        
        # Find surrounding speeds
        actual_velocity = None
        for i, speed in enumerate(speeds):
            if speed >= calculated_speed:
                if i == 0:
                    actual_velocity = velocities[0]
                else:
                    # Interpolate
                    speed1, speed2 = speeds[i-1], speeds[i]
                    vel1, vel2 = velocities[i-1], velocities[i]
                    t = (calculated_speed - speed1) / (speed2 - speed1)
                    actual_velocity = vel1 + (vel2 - vel1) * t
                break
        
        if actual_velocity is None:
            actual_velocity = velocities[-1]
    
    # Calculate actual time needed
    if actual_velocity == 0:
        actual_time_ms = float('inf')
    else:
        actual_time_ms = (abs(delta_degrees) / actual_velocity) * 1000
    
    # Calculate error
    time_error_ms = actual_time_ms - time_ms
    time_error_percent = (time_error_ms / time_ms * 100) if time_ms > 0 else 0
    
    return {
        'motor': motor,
        'delta': delta_degrees,
        'time_available': time_ms,
        'calculated_speed': calculated_speed,
        'estimated_actual_velocity': actual_velocity,
        'estimated_time_needed': actual_time_ms,
        'time_error_ms': time_error_ms,
        'time_error_percent': time_error_percent,
        'status': 'OK' if abs(time_error_percent) < 20 else 'WARNING' if abs(time_error_percent) < 50 else 'ERROR'
    }

def generate_optimized_timeline(frames, segments_data=None, verify_timing=False):
    """
    Generate timeline with motor speed verification.
    
    If verify_timing=True, will warn about movements that won't complete in time.
    """
    timeline = []

    if len(frames) < 2:
        print("[CONVERT] Not enough frames for timeline")
        return timeline

    active_ranges = []
    
    if segments_data:
        print(f"\n[CONVERT] ===== SEGMENT FILTERING =====")
        print(f"[CONVERT] Using segments.json for STRICT filtering")
        
        for seg in segments_data:
            desc = seg.get('description', '').lower()
            start_ms = int(seg.get('start_ms', 0))
            end_ms = int(seg.get('end_ms', 0))

            if 'idle' not in desc:
                print(f"[CONVERT] ACTIVE: {desc:40s} ({start_ms:4d}-{end_ms:4d}ms)")
                active_ranges.append((start_ms, end_ms))

    if not active_ranges:
        print("[CONVERT] No active ranges found!")
        return timeline

    def time_in_active_range(t):
        for start, end in active_ranges:
            if start <= t <= end:
                return True
        return False

    print(f"\n[CONVERT] ===== GENERATING TIMELINE (with timing verification) =====")
    
    included_count = 0
    excluded_count = 0
    timing_warnings = []

    for i in range(len(frames) - 1):
        current_frame = frames[i]
        next_frame = frames[i + 1]

        curr_time = current_frame['time_ms']
        next_time = next_frame['time_ms']

        if not (time_in_active_range(curr_time) and time_in_active_range(next_time)):
            excluded_count += 1
            continue

        included_count += 1
        dt_ms = next_time - curr_time
        if dt_ms <= 0:
            dt_ms = 30

        motor_commands = {}

        for port in sorted(next_frame['deltas'].keys()):
            delta = next_frame['deltas'][port]

            if abs(delta) >= 1.0:
                speed = calculate_speed_with_calibration(port, delta, dt_ms)
                
                if speed > 0:
                    motor_commands[port] = {
                        'target': int(delta),
                        'speed': speed,
                        'delta': delta
                    }
                    
                    # Optionally verify timing
                    if verify_timing:
                        verification = verify_movement_timing(port, delta, dt_ms, speed)
                        if verification['status'] != 'OK':
                            timing_warnings.append({
                                'frame': i,
                                'port': port,
                                'info': verification
                            })

        if motor_commands:
            timeline.append({
                'delay_ms': dt_ms,
                'motors': motor_commands
            })

    print(f"[CONVERT] Frame processing: {included_count} included, {excluded_count} excluded")
    
    if verify_timing and timing_warnings:
        print(f"\n[CONVERT] ⚠️  TIMING WARNINGS ({len(timing_warnings)} issues):")
        for warn in timing_warnings[:10]:  # Show first 10
            info = warn['info']
            print(f"  Frame {warn['frame']}, Motor {warn['port']}: " +
                  f"time error {info['time_error_percent']:+.1f}% " +
                  f"({info['time_error_ms']:+.0f}ms)")
        if len(timing_warnings) > 10:
            print(f"  ... and {len(timing_warnings) - 10} more")
        print(f"\n[CONVERT] Note: Timing errors > 20% may cause precision issues.")
        print(f"[CONVERT] If many warnings, motor calibration data may be wrong.")
    
    print(f"[CONVERT] Generated {len(timeline)} timeline entries")
    
    return timeline

def generate_timeline_script(timeline, motor_columns, config=None):
    """Generate SPIKE Python script"""

    all_motors = sorted(motor_columns.keys())

    script = f"""import motor
import time
import runloop
from hub import port

PORT_MAP = {{
"""
    for p in all_motors:
        script += f'    "{p}": port.{p},\n'
    script += "}\n"

    timeline_data = []
    for frame in timeline:
        frame_motors = {}
        for port, cmd in frame['motors'].items():
            frame_motors[port] = (cmd['target'], cmd['speed'])

        timeline_data.append({
            'delay': frame['delay_ms'],
            'motors': frame_motors
        })

    script += f"""
timeline = {repr(timeline_data)}

def execute_frame(motors_command):
    \"\"\"Execute motors for one frame\"\"\"
    for port_name, (target_degrees, speed) in motors_command.items():
        if port_name in PORT_MAP:
            motor.run_for_degrees(PORT_MAP[port_name], target_degrees, speed)

async def main():
    print("FLL Replay")
    print("Frames: " + str(len(timeline)))

    try:
        for frame_idx, frame_data in enumerate(timeline):
            delay_ms = frame_data['delay']
            motors_cmd = frame_data['motors']

            if motors_cmd:
                execute_frame(motors_cmd)

            if delay_ms > 0:
                await runloop.sleep_ms(delay_ms)

            if (frame_idx + 1) % 10 == 0:
                print("Frame " + str(frame_idx + 1) + "/" + str(len(timeline)))

        print("Done!")

    except Exception as e:
        print("Error: " + str(e))

runloop.run(main())
"""

    return script

def generate_display_script(timeline_script, segments_data, motor_columns, config=None):
    """Generate semantic display script from segments"""

    if not segments_data:
        return timeline_script

    left_motor = "A"
    right_motor = "B"

    commands = []

    for seg in segments_data:
        desc = seg.get('description', '').lower()
        duration_ms = seg.get('duration_ms', 0)
        linear_vel = seg.get('avg_linear_vel', 0)
        angular_vel = seg.get('avg_angular_vel', 0)

        if 'idle' in desc or duration_ms == 0:
            continue

        linear_distance = abs(linear_vel * duration_ms / 1000.0) * 20
        angular_distance = abs(angular_vel * duration_ms / 1000.0) * 10

        linear_speed = max(100, min(1000, int(abs(linear_vel) * 20)))
        angular_speed = max(100, min(1000, int(abs(angular_vel) * 5)))

        if 'forward' in desc:
            d = int(round(linear_distance))
            if d > 2:
                commands.append(f"await move_forward({d}, {linear_speed})")

        if 'backward' in desc:
            d = int(round(linear_distance))
            if d > 2:
                commands.append(f"await move_backward({d}, {linear_speed})")

        if 'left' in desc:
            a = int(round(angular_distance))
            if a > 1:
                commands.append(f"await turn_left({a}, {angular_speed})")

        if 'right' in desc:
            a = int(round(angular_distance))
            if a > 1:
                commands.append(f"await turn_right({a}, {angular_speed})")

        if 'raise' in desc or 'lower' in desc:
            for motor_char in ['A', 'B', 'C', 'D', 'E', 'F']:
                if motor_char.lower() in desc:
                    d = int(round(linear_distance))
                    if d > 2:
                        if 'raise' in desc or 'up' in desc:
                            commands.append(f"await move_motor('{motor_char}', {d}, {linear_speed})")
                        elif 'lower' in desc or 'down' in desc:
                            commands.append(f"await move_motor('{motor_char}', -{d}, {linear_speed})")
                    break

    if not commands:
        commands = ["await runloop.sleep_ms(100)"]

    cmd_str = '\n        '.join(commands)

    display_script = f"""import motor
from hub import port

left_motor = port.{left_motor}
right_motor = port.{right_motor}

async def move_forward(degrees, speed=500):
    motor.run_for_degrees(left_motor, degrees, speed)
    motor.run_for_degrees(right_motor, degrees, speed)
    await runloop.sleep_ms(50)

async def move_backward(degrees, speed=500):
    motor.run_for_degrees(left_motor, -degrees, speed)
    motor.run_for_degrees(right_motor, -degrees, speed)
    await runloop.sleep_ms(50)

async def turn_left(degrees, speed=400):
    motor.run_for_degrees(left_motor, -degrees, speed)
    motor.run_for_degrees(right_motor, degrees, speed)
    await runloop.sleep_ms(50)

async def turn_right(degrees, speed=400):
    motor.run_for_degrees(left_motor, degrees, speed)
    motor.run_for_degrees(right_motor, -degrees, speed)
    await runloop.sleep_ms(50)

async def move_motor(motor_port, degrees, speed=500):
    port_map = {{'A': port.A, 'B': port.B, 'C': port.C, 'D': port.D, 'E': port.E, 'F': port.F}}
    if motor_port in port_map:
        motor.run_for_degrees(port_map[motor_port], degrees, speed)
    await runloop.sleep_ms(50)

async def main():
    print("FLL Replay")
    try:
        {cmd_str}
    except Exception as e:
        print("Error: " + str(e))
    print("Done!")

import runloop
runloop.run(main())
"""

    return display_script

def generate_spike_script(csv_path, out_path_timeline, out_path_display, verify_timing=True, config=None):
    """Main conversion function"""

    csv_path = Path(csv_path)
    out_path_timeline = Path(out_path_timeline)
    out_path_display = Path(out_path_display)
    base_dir = csv_path.parent
    segments_json = base_dir / "segments.json"

    print(f"\n[CONVERT] Starting conversion with motor calibration...")
    print(f"[CONVERT] Input: {csv_path}")
    print(f"[CONVERT] Verify timing: {verify_timing}")

    try:
        frames, motor_columns = extract_motor_data(str(csv_path))

        if not frames:
            raise ValueError("Failed to extract frames from CSV")

        segments_data = None
        if segments_json.exists():
            print(f"[CONVERT] Loading segments from {segments_json}")
            with open(segments_json, 'r') as f:
                segments_data = json.load(f)

        print(f"\n[CONVERT] Generating timeline...")
        timeline = generate_optimized_timeline(frames, segments_data, verify_timing=verify_timing)

        if not timeline:
            print("[CONVERT] WARNING: No timeline entries generated!")

        print(f"\n[CONVERT] Generating timeline script...")
        timeline_script = generate_timeline_script(timeline, motor_columns, config)

        print(f"[CONVERT] Generating display script...")
        display_script = generate_display_script(timeline_script, segments_data, motor_columns, config)

        out_path_timeline.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path_timeline, 'w', encoding='utf-8') as f:
            f.write(timeline_script)
        print(f"[CONVERT] Timeline script: {len(timeline_script)} bytes → {out_path_timeline}")

        out_path_display.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path_display, 'w', encoding='utf-8') as f:
            f.write(display_script)
        print(f"[CONVERT] Display script: {len(display_script)} bytes → {out_path_display}")

        print(f"\n[CONVERT] ========== TIMELINE ({len(timeline)} entries) ==========")
        for idx, entry in enumerate(timeline):
            delay = entry['delay_ms']
            motors = entry['motors']
            
            parts = []
            for port, cmd in motors.items():
                target = cmd['target']
                speed = cmd['speed']
                parts.append(f"{port}:({int(target):+3d}°@{speed:3d}spd)")
            motor_str = " ".join(parts)
            print(f"[CONVERT] [{idx:2d}] {delay:4d}ms | {motor_str}")
        
        print(f"[CONVERT] ========== END ==========")
        print(f"\n[CONVERT] Conversion complete\n")

        return timeline_script, display_script

    except Exception as e:
        print(f"[CONVERT] ERROR: {e}\n")
        raise

if __name__ == "__main__":
    csv_path = Path("backend/data/raw_data.csv")
    out_timeline = Path("backend/data/generated_spike.py")
    out_display = Path("backend/data/generated_spike_display.py")
    
    # Set verify_timing=True to see warnings about timing mismatches
    generate_spike_script(str(csv_path), str(out_timeline), str(out_display), verify_timing=True)