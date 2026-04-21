import csv
import os
from typing import List, Dict


# load csv file
def load_rows(csv_path: str) -> List[Dict]:
    rows = []

    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)

        for r in reader:
            if r['time_ms'].strip().startswith('#'):
                continue

            rows.append({
                't': int(float(r['time_ms'])),
                'a_rel': float(r['motorA_rel_deg']),
                'b_rel': float(r['motorB_rel_deg']),
            })

    return rows


# data smoothening
def smooth_rows(rows, alpha=0.35):
    if not rows:
        return rows

    smoothed = [rows[0].copy()]

    for i in range(1, len(rows)):
        prev = smoothed[-1]
        cur = rows[i]

        da = alpha * cur['a_rel'] + (1 - alpha) * prev['a_rel']
        db = alpha * cur['b_rel'] + (1 - alpha) * prev['b_rel']

        smoothed.append({
            't': cur['t'],
            'a_rel': da,
            'b_rel': db
        })

    return smoothed


# timeline generation
def build_timeline(rows):
    timeline = []

    prev = rows[0]

    for r in rows[1:]:
        dt = r['t'] - prev['t']
        da = int(r['a_rel'] - prev['a_rel'])
        db = int(r['b_rel'] - prev['b_rel'])

        # deadzone (removes jitter)
        if abs(da) < 2:
            da = 0
        if abs(db) < 2:
            db = 0

        timeline.append((dt, da, db, 0))
        prev = r

    return timeline


# create spike script content
def generate_spike_script(csv_path: str, out_path: str):
    rows = load_rows(csv_path)
    rows = smooth_rows(rows)

    timeline = build_timeline(rows)

    content = """import runloop
import motor
from hub import port

# AUTO-GENERATED SMOOTHED REPLAY

timeline = {timeline}

async def main():
    for dt, da, db, dc in timeline:

        if dt > 0:
            await runloop.sleep_ms(dt)

        # run motors together (SPIKE-safe parallel start)
        if da != 0:
            motor.run_for_degrees(port.A, da, 1000)

        if db != 0:
            motor.run_for_degrees(port.B, db, 1000)

    print("Replay complete")

runloop.run(main())
""".format(timeline=timeline)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w") as f:
        f.write(content)

    print("Saved:", out_path)


# output replay file
if __name__ == "__main__":
    generate_spike_script(
        r"C:\Users\rickh\FLLDataCollection\circle.csv",
        r"C:\Users\rickh\FLLDataCollection\circle_replay.py"
    )