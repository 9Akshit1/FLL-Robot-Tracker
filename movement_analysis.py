import csv
from dataclasses import dataclass
from typing import List

# Data
@dataclass
class DataPoint:
    t: float
    a_rel: float
    a_abs: float
    b_rel: float
    b_abs: float
    c_rel: float
    c_abs: float
    yaw: float
    pitch: float
    roll: float

@dataclass
class MovementSegment:
    start_time: float
    end_time: float
    label: str
    confidence: float

# Load CSV
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
                    c_rel=float(r["motorC_rel_deg"]),
                    c_abs=float(r["motorC_abs_deg"]),
                    yaw=float(r["yaw_deg"]),
                    pitch=float(r["pitch_deg"]),
                    roll=float(r["roll_deg"]),
                )
            )
    return data

# Smoothing
def moving_average(vals, w=5):
    out = []
    for i in range(len(vals)):
        s = max(0, i - w + 1)
        out.append(sum(vals[s:i+1]) / (i - s + 1))
    return out

def smooth_data(data):
    yaw_s = moving_average([d.yaw for d in data])
    for i, d in enumerate(data):
        d.yaw = yaw_s[i]
    return data

# Feature extraction
def velocities(data):
    drive_v = [0]
    arm_v = [0]
    yaw_v = [0]

    for i in range(1, len(data)):
        dt = (data[i].t - data[i-1].t) / 1000
        if dt <= 0:
            drive_v.append(0)
            arm_v.append(0)
            yaw_v.append(0)
            continue

        drive = ((data[i].a_rel - data[i-1].a_rel) +
                 (data[i].b_rel - data[i-1].b_rel)) / 2 / dt

        arm = (data[i].c_rel - data[i-1].c_rel) / dt
        yaw_rate = (data[i].yaw - data[i-1].yaw) / dt

        drive_v.append(drive)
        arm_v.append(arm)
        yaw_v.append(yaw_rate)

    return drive_v, arm_v, yaw_v

# Classification
def classify_movements(data):
    segments = []
    drive_v, arm_v, yaw_v = velocities(data)

    DRIVE_TH = 15      # deg/s
    ARM_TH   = 15      # deg/s
    YAW_TH   = 15      # deg/s
    MIN_SEGMENT_MS = 200

    current = None
    start_t = data[0].t

    for i in range(len(data)):
        label = "stationary"

        if abs(arm_v[i]) > ARM_TH:
            label = "arm_moving"
        elif abs(drive_v[i]) > DRIVE_TH:
            if abs(yaw_v[i]) > YAW_TH:
                label = "turning"
            else:
                label = "driving_straight"

        if label != current:
            if current is not None:
                if data[i].t - start_t >= MIN_SEGMENT_MS:
                    segments.append(
                        MovementSegment(start_t, data[i].t, current, 0.85)    # confidence is fixed for now
                    )
            current = label
            start_t = data[i].t

    return segments

# Pipeline
def run_pipeline(csv_path):
    data = smooth_data(load_data(csv_path))
    segments = classify_movements(data)
    for s in segments:
        print(s)

# Run the pipeline
run_pipeline("cleaned_data.csv")