# ============================================================
# movement_analysis.py - Dynamic Column Support
# ============================================================

import csv
import os
from typing import List, Dict
from pathlib import Path
import json

class DataPoint:
    def __init__(self, data_dict):
        self.t = float(data_dict.get("time_ms", 0))
        
        # Motor data - dynamically extract
        self.motors = {}
        for key, val in data_dict.items():
            if "_rel_deg" in key or "_abs_deg" in key:
                self.motors[key] = float(val)
        
        # Sensor data - dynamically extract
        self.sensors = {}
        for key, val in data_dict.items():
            if "_mm" in key or "_N" in key:
                self.sensors[key] = float(val)
        
        # IMU data
        self.yaw = float(data_dict.get("yaw_deg", 0))
        self.pitch = float(data_dict.get("pitch_deg", 0))
        self.roll = float(data_dict.get("roll_deg", 0))

def load_data(csv_path):
    data = []
    with open(csv_path, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [name.replace("\ufeff", "") for name in reader.fieldnames]
        print("Clean headers:", reader.fieldnames)
        
        for r in reader:
            if not r.get("time_ms") or str(r["time_ms"]).startswith("#"):
                continue
            
            data.append(DataPoint(r))
    return data

def unwrap_angles(deg_list):
    if not deg_list:
        return []
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

def calculate_speed(motor_a_change, motor_b_change, dt_sec):
    """Calculate forward speed"""
    if dt_sec <= 0:
        return 0
    avg_speed = ((motor_a_change + motor_b_change) / 2) / dt_sec
    return avg_speed

def velocities(data, config=None):
    if not data:
        return [], []
    
    drive_v = [0]
    yaw_v = [0]
    
    yaw_unwrapped = unwrap_angles([d.yaw for d in data])
    
    # Get motor ports from config
    motor_ports = []
    if config and "motors" in config:
        motor_ports = [p for p, enabled in config["motors"].items() if enabled]
    
    if not motor_ports:
        motor_ports = ["A", "B"]  # fallback

    for i in range(1, len(data)):
        dt = (data[i].t - data[i - 1].t) / 1000.0
        if dt <= 0:
            drive_v.append(0)
            yaw_v.append(0)
            continue

        # Find motor changes dynamically
        motor_changes = []
        
        for port in motor_ports:
            motor_key = f"motor{port}_rel_deg"
            if motor_key in data[i].motors and motor_key in data[i-1].motors:
                delta = data[i].motors[motor_key] - data[i-1].motors[motor_key]
                motor_changes.append(delta)
        
        # Calculate speed based on available motors
        if motor_changes:
            drive = calculate_speed(motor_changes[0], motor_changes[1] if len(motor_changes) > 1 else motor_changes[0], dt)
        else:
            drive = 0
        
        yaw_rate = (yaw_unwrapped[i] - yaw_unwrapped[i - 1]) / dt

        drive_v.append(drive)
        yaw_v.append(yaw_rate)

    return drive_v, yaw_v

def classify_movements(data, config=None):
    segments = []
    drive_v, yaw_v = velocities(data, config)

    DRIVE_THRESHOLD = 12
    YAW_THRESHOLD = 12
    MIN_SEGMENT_MS = 200

    current = None
    start_t = data[0].t
    start_idx = 0

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
                    avg_speed = sum(drive_v[start_idx:i]) / max(1, i - start_idx)
                    segments.append({
                        'start': start_t,
                        'end': data[i].t,
                        'type': current,
                        'avg_speed': round(avg_speed, 2),
                        'duration': round((data[i].t - start_t) / 1000, 2)
                    })
            current = label
            start_t = data[i].t
            start_idx = i

    return segments

def run(csv_path, config=None):
    data = load_data(csv_path)
    segments = classify_movements(data, config)
    return segments

if __name__ == "__main__":
    INPUT_FILE = Path("backend/data/raw_data.csv")
    OUTPUT_FILE = Path("backend/data/segments.csv")

    segments = run(str(INPUT_FILE))

    print("\nDetected Segments:")
    for s in segments:
        print(f"[{s['start']:.0f} - {s['end']:.0f}] {s['type']:20} Speed: {s['avg_speed']:6.2f} deg/s Duration: {s['duration']:.2f}s")