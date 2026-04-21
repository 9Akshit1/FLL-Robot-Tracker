import csv
import os
from typing import List, Dict


# load csv file (keeps ALL columns)
def load_rows(csv_path: str) -> List[Dict]:
    rows = []

    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)

        for r in reader:
            if r['time_ms'].strip().startswith('#'):
                continue

            # convert everything to float/int when possible
            row = {}
            for k, v in r.items():
                v = v.strip()

                if v == "":
                    row[k] = None
                    continue

                try:
                    # time_ms should be int
                    if k == "time_ms":
                        row[k] = int(float(v))
                    else:
                        row[k] = float(v)
                except:
                    row[k] = v  # keep as string if conversion fails

            rows.append(row)

    return rows


# timeline generation using motor relative degrees
def build_timeline(rows):
    timeline = []

    prev = rows[0]

    for r in rows[1:]:
        dt = r["time_ms"] - prev["time_ms"]

        da = int(r["motorA_rel_deg"] - prev["motorA_rel_deg"])
        db = int(r["motorB_rel_deg"] - prev["motorB_rel_deg"])

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

    timeline = build_timeline(rows)

    content = f"""import runloop
import motor
from hub import port

# AUTO-GENERATED REPLAY (FULL RAW DATA INCLUDED)

raw_data = {rows}

timeline = {timeline}

async def main():
    for dt, da, db, dc in timeline:

        if dt > 0:
            await runloop.sleep_ms(dt)

        if da != 0:
            motor.run_for_degrees(port.A, da, 1000)

        if db != 0:
            motor.run_for_degrees(port.B, db, 1000)

    print("Replay complete")
    print("Raw data points loaded:", len(raw_data))

runloop.run(main())
"""

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w") as f:
        f.write(content)

    print("Saved:", out_path)


# output replay file
if __name__ == "__main__":
    generate_spike_script(
        r"C:\\Users\\rickh\\FLLDataCollection\\circle.csv",
        r"C:\\Users\\rickh\\FLLDataCollection\\circle_replay2.py"
    )