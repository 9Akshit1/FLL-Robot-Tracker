# ============================================================
# convert_to_code.py - Timeline replay + Semantic display
# ============================================================

import json
import csv
from pathlib import Path

def generate_spike_script(csv_path, out_path, config=None):
    """
    1. Actual replay uploaded: timeline from raw CSV (with smoothing for noise)
    2. UI display: semantic commands (move_forward, turn_left, etc.)
    """
    
    csv_path = Path(csv_path)
    out_path = Path(out_path)
    base_dir = csv_path.parent
    segments_json = base_dir / "segments.json"
    
    print(f"[CONVERT] Reading raw CSV for timeline...")
    
    # ========== EXTRACT TIMELINE FROM RAW CSV WITH SMOOTHING ==========
    raw_data = []
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    time_ms = int(float(row.get('time_ms', 0)))
                    motor_a = 0
                    motor_b = 0
                    
                    # Find motor columns
                    for key in row.keys():
                        key_clean = key.replace('\ufeff', '').strip()
                        if 'motorA' in key_clean or 'motor_A' in key_clean:
                            motor_a = int(float(row.get(key, 0)))
                        elif 'motorB' in key_clean or 'motor_B' in key_clean:
                            motor_b = int(float(row.get(key, 0)))
                    
                    raw_data.append((time_ms, motor_a, motor_b))
                except:
                    continue
        
        print(f"[CONVERT] Loaded {len(raw_data)} raw data points")
    except Exception as e:
        print(f"[CONVERT] ERROR reading CSV: {e}")
        raise
    
    # Convert to timeline with smoothing for noise
    timeline = []
    if raw_data:
        prev_time = raw_data[0][0]
        prev_a = raw_data[0][1]
        prev_b = raw_data[0][2]
        
        for time_ms, motor_a, motor_b in raw_data[1:]:
            dt = time_ms - prev_time
            da = motor_a - prev_a
            db = motor_b - prev_b
            
            # Filter out noise: ignore very small movements in single samples
            # (but keep them if they accumulate)
            if dt > 0 or abs(da) > 1 or abs(db) > 1:
                timeline.append((dt, da, db, 0))
                prev_time = time_ms
                prev_a = motor_a
                prev_b = motor_b
        
        print(f"[CONVERT] Generated timeline with {len(timeline)} entries (noise filtered)")
    
    # Motor config
    left_motor = "A"
    right_motor = "B"
    if config and "motors" in config:
        for port, role in config.items():
            if role == "left_drive":
                left_motor = port
            elif role == "right_drive":
                right_motor = port
    
    print(f"[CONVERT] Motors: left={left_motor}, right={right_motor}")
    
    # ========== WRITE ACTUAL REPLAY (timeline) TO ROBOT ==========
    timeline_code = f"""import runloop
import motor
from hub import port

# Raw replay with noise filtering
timeline = {timeline}

async def main():
    print("Starting replay...")
    try:
        for dt, da, db, dc in timeline:
            if dt > 0:
                await runloop.sleep_ms(dt)
            
            if da != 0:
                motor.run_for_degrees(port.{left_motor}, da, 1000)
            
            if db != 0:
                motor.run_for_degrees(port.{right_motor}, db, 1000)
    except Exception as e:
        print(f"Error: {{e}}")
    
    print("Replay complete")

runloop.run(main())
"""
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(timeline_code)
    
    print(f"[CONVERT] Written ACTUAL replay (timeline) to {out_path}")
    print(f"[CONVERT] Size: {len(timeline_code)} bytes")
    
    # ========== GENERATE SEMANTIC DISPLAY VERSION FOR UI ==========
    if not segments_json.exists():
        print(f"[CONVERT] No segments - using timeline for display")
        display_script = timeline_code
    else:
        try:
            with open(segments_json, 'r') as f:
                segments = json.loads(f.read())
            
            commands = []
            for seg in segments:
                desc = seg.get('description', '').lower()
                dur = seg.get('duration_ms', 0)
                lin = seg.get('avg_linear_vel', 0)
                ang = seg.get('avg_angular_vel', 0)
                
                if 'idle' in desc or dur == 0 or (lin == 0 and ang == 0):
                    continue
                
                dist = abs(lin * dur / 1000.0) * 20
                angle = abs(ang * dur / 1000.0) * 10
                speed = max(100, min(1000, int(abs(lin) * 20)))
                turn_speed = max(100, min(1000, int(abs(ang) * 5)))
                
                if 'forward' in desc:
                    d = int(round(dist))
                    if d > 2:
                        commands.append(f"await move_forward({d}, {speed})")
                elif 'backward' in desc:
                    d = int(round(dist))
                    if d > 2:
                        commands.append(f"await move_backward({d}, {speed})")
                elif 'left' in desc:
                    a = int(round(angle))
                    if a > 1:
                        commands.append(f"await turn_left({a}, {turn_speed})")
                elif 'right' in desc:
                    a = int(round(angle))
                    if a > 1:
                        commands.append(f"await turn_right({a}, {turn_speed})")
            
            if not commands:
                commands = ["await runloop.sleep_ms(100)"]
            
            print(f"[CONVERT] Display commands: {len(commands)}")
            
            cmd_str = '\n    '.join(commands)
            
            # DISPLAY SCRIPT - clean semantic version for UI
            display_script = f"""import motor
from hub import port

left_motor = port.{left_motor}
right_motor = port.{right_motor}

async def move_forward(degrees, speed=500):
    motor.run_for_degrees(left_motor, degrees, speed)
    motor.run_for_degrees(right_motor, degrees, speed)
    await runloop.sleep_ms(100)

async def move_backward(degrees, speed=500):
    motor.run_for_degrees(left_motor, -degrees, speed)
    motor.run_for_degrees(right_motor, -degrees, speed)
    await runloop.sleep_ms(100)

async def turn_left(degrees, speed=400):
    motor.run_for_degrees(left_motor, -degrees, speed)
    motor.run_for_degrees(right_motor, degrees, speed)
    await runloop.sleep_ms(100)

async def turn_right(degrees, speed=400):
    motor.run_for_degrees(left_motor, degrees, speed)
    motor.run_for_degrees(right_motor, -degrees, speed)
    await runloop.sleep_ms(100)

async def main():
    print("Starting replay...")
    try:
        {cmd_str}
    except Exception as e:
        print(f"Error: {{e}}")
    print("Done!")

import runloop
runloop.run(main())
"""
        
        except Exception as e:
            print(f"[CONVERT] Error generating display: {e}")
            display_script = timeline_code
    
    print(f"[CONVERT] Display script size: {len(display_script)} bytes")
    
    return out_path, display_script

if __name__ == "__main__":
    from pathlib import Path
    csv_path = Path("backend/data/raw_data.csv")
    out_path = Path("backend/data/generated_spike.py")
    generate_spike_script(str(csv_path), str(out_path))