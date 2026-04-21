import csv
import os
from typing import List, Dict


def load_rows(csv_path: str) -> List[Dict]:
    rows = []

    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)

        for r in reader:
            if r['time_ms'].strip().startswith('#'):
                continue

            rows.append({
                't': int(float(r['time_ms'])),
                'a_rel': int(float(r['motorA_rel_deg'])),
                'b_rel': int(float(r['motorB_rel_deg'])),
                'c_rel': int(float(r.get('motorC_rel_deg', 0) or 0)),
            })

    return rows


def generate_spike_script(csv_path: str, out_path: str) -> str:
    print("Loading CSV from:", csv_path)

    rows = load_rows(csv_path)

    print("Rows loaded:", len(rows))

    if not rows:
        raise RuntimeError("No data loaded.")

    timeline = []
    prev = rows[0].copy()

    for r in rows[1:]:
        dt = r['t'] - prev['t']
        da = r['a_rel'] - prev['a_rel']
        db = r['b_rel'] - prev['b_rel']
        dc = r['c_rel'] - prev['c_rel']

        timeline.append((dt, da, db, dc))
        prev = r

    content = """import runloop
import motor
from hub import port

# AUTO-GENERATED FILE

timeline = {timeline}

async def main():
    for dt, da, db, dc in timeline:

        if dt > 0:
            await runloop.sleep_ms(dt)

        if da != 0:
            await motor.run_for_degrees(port.A, da, 500)

        if db != 0:
            await motor.run_for_degrees(port.B, db, 500)

        if dc != 0:
            await motor.run_for_degrees(port.C, dc, 500)

    print("Replay complete")

runloop.run(main())
""".format(timeline=timeline)

    # Ensure folder exists
    folder = os.path.dirname(out_path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(out_path, "w") as f:
        f.write(content)

    print("WROTE FILE:", out_path)

    return out_path


if __name__ == "__main__":
    csv_file = r"C:\Users\rickh\FLLDataCollection\log3.csv"
    output_file = r"C:\Users\rickh\FLLDataCollection\replay3.py"

    out = generate_spike_script(csv_file, output_file)

    print("Generated file at:", out)