import csv
from typing import List

# Data class
class DataPoint:
    """This class if simply to make it easier to work and access the data."""
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

# Load CSV
def load_data(csv_path):
    data = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["time_ms"].startswith("#"):
                continue

            # Instead of working with the raw CSV data, we convert it into a list of DataPoint objects. 
            # This makes it easier to work with the data later on, because we can access the fields by name instead of by index.
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
def ema(vals, alpha=0.2):
    """Exponential Moving Average smoothing.""" 
    out = [vals[0]]
    for i in range(1, len(vals)):
        out.append(alpha * vals[i] + (1 - alpha) * out[-1])
    return out

# Feature extraction
def unwrap_angles(deg_list):
    """Fix 180° to -180° wraparound jumps."""
    unwrapped = [deg_list[0]]
    offset = 0

    for i in range(1, len(deg_list)):
        delta = deg_list[i] - deg_list[i-1]

        if delta > 180:
            offset -= 360
        elif delta < -180:
            offset += 360

        unwrapped.append(deg_list[i] + offset)

    return unwrapped

def velocities(data):
    drive_v = [0]
    arm_v = [0]
    yaw_v = [0]
     
    yaw_unwrapped = unwrap_angles([d.yaw for d in data])    # unwrap the yaws, because if we dont do this, then the code will consider a -179° to 179° jump as a 358° movement, which is not correct.

    for i in range(1, len(data)):
        dt = (data[i].t - data[i-1].t) / 1000  # ms to s

        if dt <= 0:
            drive_v.append(0)
            arm_v.append(0)
            yaw_v.append(0)
            continue

        # Calculate the velocities
        drive = (
            (data[i].a_rel - data[i-1].a_rel) / dt +
            (data[i].b_rel - data[i-1].b_rel) / dt
        ) / 2

        arm = (data[i].c_rel - data[i-1].c_rel) / dt
        yaw_rate = (yaw_unwrapped[i] - yaw_unwrapped[i-1]) / dt

        drive_v.append(drive)
        arm_v.append(arm)
        yaw_v.append(yaw_rate)

    # Smooth the velocities to reduce noise. 
    # The alpha value is hardcoded for now, but we might want to experiment with it later on.
    drive_v = ema(drive_v, alpha=0.2)
    arm_v   = ema(arm_v, alpha=0.2)
    yaw_v   = ema(yaw_v, alpha=0.2)

    return drive_v, arm_v, yaw_v

# Classification
def classify_movements(data):
    segments = []
    drive_v, arm_v, yaw_v = velocities(data)

    # These are all hardcoded for now....They allow us to classify "significant-enough" movements based on the velocities.
    # In the future, we might need to think of a more robust way to classify (e.g. using a machine learning model). 
    DRIVE_THRESHOLD = 12    # deg/s
    ARM_THRESHOLD = 12      # deg/s
    YAW_THRESHOLD = 12      # deg/s
    MIN_SEGMENT_MS = 200    # minimum duration for a segment to be valid

    current = None
    start_t = data[0].t

    for i in range(len(data)):
        label = "stationary"

        if abs(arm_v[i]) > ARM_THRESHOLD:
            if arm_v[i] > 0:
                label = "raising_arm"
            else:
                label = "lowering_arm"
        
        if abs(drive_v[i]) > DRIVE_THRESHOLD:
            if abs(yaw_v[i]) > YAW_THRESHOLD:
                if yaw_v[i] > 0:
                    label = "turning_left"
                else:
                    label = "turning_right"
            else:
                label = "driving_straight"

        if label != current:
            if current is not None:
                if data[i].t - start_t >= MIN_SEGMENT_MS:
                    segments.append(
                        [start_t, data[i].t, current]
                    )
            current = label
            start_t = data[i].t
    
    # Do the last segment if we ended while still in a movement
    if current is not None:
        if data[-1].t - start_t >= MIN_SEGMENT_MS:
            segments.append([start_t, data[-1].t, current])

    return segments

# Pipeline
def run(csv_path):
    raw_data = load_data(csv_path)
    segments = classify_movements(raw_data)
    for s in segments:
        print(f"Segment: {s[0]:.2f}ms to {s[1]:.2f}ms - {s[2]}")

# Run the pipeline
run("cleaned_data.csv")