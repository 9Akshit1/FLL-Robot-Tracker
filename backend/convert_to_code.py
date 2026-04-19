# ============================================================
# convert_to_code.py - Dynamic Motor Support
# ============================================================

import csv
from typing import List, Dict
import os
from pathlib import Path
import json

def load_rows(csv_path):
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
            
            for key, val in r.items():
                if "_rel_deg" in key:
                    # Extract motor letter (A, B, C, etc)
                    motor_letter = key.split('motor')[1][0]
                    row[f'{motor_letter}_rel'] = int(float(val))

            rows.append(row)

    print("Loaded rows:", len(rows))
    return rows

def generate_spike_script(csv_path, out_path):
    rows = load_rows(csv_path)
    if not rows:
        raise RuntimeError("No data loaded.")

    timeline = []
    prev = rows[0].copy()

    for r in rows[1:]:
        dt = r['t'] - prev['t']
        
        # Build motion tuple dynamically
        motion = [dt]
        
        # Add motor deltas in order (A, B, C...)
        for motor in ['A', 'B', 'C']:
            motor_key = f'{motor}_rel'
            if motor_key in r and motor_key in prev:
                delta = r[motor_key] - prev[motor_key]
            else:
                delta = 0
            motion.append(delta)
        
        timeline.append(tuple(motion))
        prev = r.copy()

    content = f"""import runloop
import motor
from hub import port

timeline = {timeline!r}

def compute_speed(deg, dt):
    if dt <= 0:
        return 0
    speed = int((abs(deg) / dt) * 1000)
    return max(100, min(speed, 1000))

async def move_motors(dt, da, db, dc):
    if da != 0:
        motor.run_for_degrees(port.A, da, compute_speed(da, dt))
    if db != 0:
        motor.run_for_degrees(port.B, db, compute_speed(db, dt))
    if dc != 0:
        motor.run_for_degrees(port.C, dc, compute_speed(dc, dt))
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

    path = generate_spike_script(str(INPUT_CSV), str(OUTPUT_SCRIPT))
    print(f"Replay script generated: {path}")