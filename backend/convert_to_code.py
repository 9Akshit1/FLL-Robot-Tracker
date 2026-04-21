# ============================================================
# convert_to_code.py - Dynamic Motor Support
# ============================================================

import csv
from typing import List, Dict
import os
from pathlib import Path
import json

def load_rows(csv_path, config=None):
    rows = []

    with open(csv_path, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [name.replace("\ufeff", "") for name in reader.fieldnames]
        print("Clean headers:", reader.fieldnames)

        for r in reader:
            if not r.get("time_ms") or str(r["time_ms"]).strip().startswith('#'):
                continue

            # Dynamically extract motor data
            row = {'t': int(float(r['time_ms']))}
            
            # Get motor ports from config
            motor_ports = []
            if config and "motors" in config:
                motor_ports = [p for p, enabled in config["motors"].items() if enabled]
            
            for key, val in r.items():
                if "_rel_deg" in key:
                    # Extract motor letter (A, B, C, etc)
                    motor_letter = key.split('motor')[1][0]
                    if not motor_ports or motor_letter in motor_ports:
                        row[f'{motor_letter}_rel'] = int(float(val))

            rows.append(row)

    print("Loaded rows:", len(rows))
    return rows

def generate_spike_script(csv_path, out_path, config=None):
    rows = load_rows(csv_path, config)
    if not rows:
        raise RuntimeError("No data loaded.")

    timeline = []
    prev = rows[0].copy()
    
    # Get motor ports from config
    motor_ports = []
    if config and "motors" in config:
        motor_ports = [p for p, enabled in config["motors"].items() if enabled]
    
    if not motor_ports:
        motor_ports = ["A", "B", "C"]  # fallback

    for r in rows[1:]:
        dt = r['t'] - prev['t']
        
        # Build motion tuple dynamically based on actual motors
        motion = [dt]
        
        # Add motor deltas in order
        for motor in motor_ports:
            motor_key = f'{motor}_rel'
            if motor_key in r and motor_key in prev:
                delta = r[motor_key] - prev[motor_key]
            else:
                delta = 0
            motion.append(delta)
        
        timeline.append(tuple(motion))
        prev = r.copy()

    # Build the move_motors function dynamically
    param_names = [f'd{p}' for p in motor_ports]
    params = ', '.join(param_names)
    
    # Build the motor control code with proper indentation
    motor_lines = []
    for port in motor_ports:
        motor_lines.append(f"    if d{port} != 0:")
        motor_lines.append(f"        motor.run_for_degrees(port.{port}, d{port}, compute_speed(d{port}, dt))")
    motor_control_code = '\n'.join(motor_lines)
    
    content = f"""import runloop
import motor
from hub import port

timeline = {timeline!r}

def compute_speed(deg, dt):
    if dt <= 0:
        return 0
    speed = int((abs(deg) / dt) * 1000)
    return max(100, min(speed, 1000))

async def move_motors(dt, {params}):
{motor_control_code}
    if dt > 0:
        await runloop.sleep_ms(dt)

async def main():
    for motion in timeline:
        await move_motors(*motion)
    print("Replay complete")

runloop.run(main())
"""

    with open(out_path, "w") as f:
        f.write(content)

    return out_path

if __name__ == "__main__":
    INPUT_CSV = Path("backend/data/raw_data.csv")
    OUTPUT_SCRIPT = Path("backend/data/replay.py")

    path = generate_spike_script(str(INPUT_CSV), str(OUTPUT_SCRIPT), config=None)
    print(f"Replay script generated: {path}")