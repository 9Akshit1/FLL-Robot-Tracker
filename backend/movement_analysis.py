import csv
import os
from typing import List

# ---------------- DATA CLASS ----------------

class DataPoint:
    def __init__(self, t=0, a_rel=0, a_abs=0, b_rel=0, b_abs=0, c_rel=0, c_abs=0, yaw=0, pitch=0, roll=0):
        self.t = t
        self.a_rel = a_rel
        self.a_abs = a_abs
        self.b_rel = b_rel
        self.b_abs = b_abs
        self.c_rel = c_rel
        self.c_abs = c_abs
        self.yaw = yaw
        self.pitch = pitch
        self.roll = roll


# ---------------- LOAD ----------------

def load_data(csv_path):
    data = []

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["time_ms"].startswith("#"):
                continue

            data.append(
                DataPoint(
                    t=float(r["time_ms"]),
                    a_rel=float(r["motorA_rel_deg"]),
                    a_abs=float(r["motorA_abs_deg"]),
                    b_rel=float(r["motorB_rel_deg"]),
                    b_abs=float(r["motorB_abs_deg"]),
                    c_rel=float(r.get("motorC_rel_deg", 0) or 0),
                    c_abs=float(r.get("motorC_abs_deg", 0) or 0),
                    yaw=float(r["yaw_deg"]),
                    pitch=float(r["pitch_deg"]),
                    roll=float(r["roll_deg"]),
                )
            )
    return data


# ---------------- ANALYSIS ----------------

def unwrap_angles(deg_list):
    unwrapped = [deg_list[0]]
    offset = 0

    for i in range(1, len(deg_list)):
        delta = deg_list[i] - deg_list[i - 1]

        if delta > 180:
            offset -= 360
        elif delta < -180:
            offset += 360

        unwrapped.append(deg_list[i] + offset)

    return unwrapped


def velocities(data):
    drive_v = [0]
    yaw_v = [0]

    yaw_unwrapped = unwrap_angles([d.yaw for d in data])

    for i in range(1, len(data)):
        dt = (data[i].t - data[i - 1].t) / 1000
        if dt <= 0:
            drive_v.append(0)
            yaw_v.append(0)
            continue

        drive = (
            (data[i].a_rel - data[i - 1].a_rel) / dt +
            (data[i].b_rel - data[i - 1].b_rel) / dt
        ) / 2

        yaw_rate = (yaw_unwrapped[i] - yaw_unwrapped[i - 1]) / dt

        drive_v.append(drive)
        yaw_v.append(yaw_rate)

    return drive_v, yaw_v


def classify_movements(data):
    segments = []
    drive_v, yaw_v = velocities(data)

    DRIVE_THRESHOLD = 12
    YAW_THRESHOLD = 12
    MIN_SEGMENT_MS = 200

    current = None
    start_t = data[0].t

    for i in range(len(data)):
        label = "stationary"

        if abs(drive_v[i]) > DRIVE_THRESHOLD:
            if abs(yaw_v[i]) > YAW_THRESHOLD:
                label = "turning_left" if yaw_v[i] > 0 else "turning_right"
            else:
                label = "driving_straight"

        if label != current:
            if current is not None:
                if data[i].t - start_t >= MIN_SEGMENT_MS:
                    segments.append([start_t, data[i].t, current])
            current = label
            start_t = data[i].t

    return segments


# ---------------- PIPELINE ----------------

def run(csv_path, output_segments_path=None):
    data = load_data(csv_path)
    segments = classify_movements(data)

    if output_segments_path:
        with open(output_segments_path, "w") as f:
            for s in segments:
                f.write(f"{s[0]},{s[1]},{s[2]}\n")

    return segments