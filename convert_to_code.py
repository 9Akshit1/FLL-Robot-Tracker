"""
Feb 23 2026
Rick
Code shouldn't be hundreds of lines long.
Timestamps added.
"""

import csv
from typing import List, Dict

# CSV LOADER
def load_rows(csv_path: str) -> List[Dict]:
    rows = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['time_ms'].strip().startswith('#'):
                continue
            rows.append({
                't': int(r['time_ms'].strip()),
                'a_rel': int(r['motorA_rel_deg'].strip()),
                'b_rel': int(r['motorB_rel_deg'].strip()),
                'c_rel': int(r['motorC_rel_deg'].strip()),
            })
    return rows

# SPIKE PYTHON GENERATOR (Official LEGO API Style)
def generate_spike_script(csv_path: str, out_path: str = 'generated_spike.py') -> None:
    """
    Generates a compact SPIKE App Python program using:

        import runloop
        import motor
        from hub import port

    Output format:
        async def main():
            ...
        runloop.run(main())
    """

    rows = load_rows(csv_path)
    if not rows:
        raise RuntimeError('no rows loaded from ' + csv_path)

    # Build compressed timeline: (dt, deltaA, deltaB, deltaC)
    timeline = []
    prev = rows[0].copy()

    for r in rows[1:]:
        dt = r['t'] - prev['t']
        da = r['a_rel'] - prev['a_rel']
        db = r['b_rel'] - prev['b_rel']
        dc = r['c_rel'] - prev['c_rel']

        timeline.append((dt, da, db, dc))
        prev = r

    # Generate SPIKE Python file
    content = """import runloop
import motor
from hub import port

# Auto-generated SPIKE replay script

timeline = """ + repr(timeline) + """

async def main():
"""

    content += """
    for dt, da, db, dc in timeline:

        # wait before next move
        if dt > 0:
            await runloop.sleep_ms(dt)

        # run motors (sequential for timing accuracy)
        if da != 0:
            await motor.run_for_degrees(port.A, da, 500)

        if db != 0:
            await motor.run_for_degrees(port.B, db, 500)

        if dc != 0:
            await motor.run_for_degrees(port.C, dc, 500)

    print("Replay complete")


runloop.run(main())
"""

    with open(out_path, "w", newline='') as f:
        f.write(content)

# Run generator directly
if __name__ == '__main__':
    generate_spike_script('cleaned_data.csv', 'generated_spike.py')
