# ============================================================
# movement_analysis.py - Vector Kinematics Movement Classification
# ============================================================

import csv
import os
from typing import List, Dict, Tuple, Set
from pathlib import Path
import json
import math

class DataPoint:
    """Single data sample from robot sensors"""
    def __init__(self, data_dict):
        self.t = float(data_dict.get("time_ms", 0))
        
        # Motor data
        self.motors = {}
        for key, val in data_dict.items():
            if "_rel_deg" in key or "_abs_deg" in key:
                try:
                    self.motors[key] = float(val)
                except (ValueError, TypeError):
                    self.motors[key] = 0.0
        
        # Sensor data
        self.sensors = {}
        for key, val in data_dict.items():
            if "_mm" in key or "_N" in key:
                try:
                    self.sensors[key] = float(val)
                except (ValueError, TypeError):
                    self.sensors[key] = 0.0
        
        # IMU
        self.yaw = float(data_dict.get("yaw_deg", 0))
        self.pitch = float(data_dict.get("pitch_deg", 0))
        self.roll = float(data_dict.get("roll_deg", 0))

def load_data(csv_path):
    """Load CSV into DataPoint objects"""
    data = []
    with open(csv_path, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [name.replace("\ufeff", "").strip() for name in reader.fieldnames]
        
        for r in reader:
            if not r.get("time_ms") or str(r.get("time_ms", "")).startswith("#"):
                continue
            
            try:
                data.append(DataPoint(r))
            except (ValueError, TypeError, KeyError):
                continue
    
    return data

def unwrap_angles(deg_list):
    """Unwrap angular values across 360 degree boundaries"""
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

# ============================================================
# VECTOR KINEMATICS ANALYSIS
# ============================================================

class KinematicState:
    """Represents motion state at a moment in time with multi-label support"""
    def __init__(self, t_ms):
        self.t = t_ms
        
        # Drive motors velocities (deg/sec)
        self.left_vel = 0.0
        self.right_vel = 0.0
        
        # Individual attachment motor velocities
        self.attachment_vels = {}  # port -> velocity
        
        # Derived kinematics
        self.linear_vel = 0.0      # forward speed
        self.angular_vel = 0.0     # rotation speed (deg/sec)
        self.left_power = 0.0      # normalized 0-1
        self.right_power = 0.0     # normalized 0-1
        
        # Multi-label classification
        self.actions = set()  # Set of concurrent actions
    
    def classify(self):
        """Classify what actions are happening RIGHT NOW"""
        self.actions = set()
        
        # Thresholds for motion detection
        LINEAR_THRESH = 10.0        # deg/sec
        ANGULAR_THRESH = 8.0        # deg/sec
        ATTACHMENT_THRESH = 15.0    # deg/sec
        
        # Calculate linear and angular velocity
        if abs(self.left_vel) > 0.1 or abs(self.right_vel) > 0.1:
            self.linear_vel = (self.left_vel + self.right_vel) / 2.0
            self.angular_vel = (self.right_vel - self.left_vel) / 2.0  # Differential drive
        
        # Multi-label classification - actions can overlap
        
        # 1. DRIVE CLASSIFICATION (forward/backward)
        if abs(self.linear_vel) > LINEAR_THRESH:
            if self.linear_vel > 0:
                self.actions.add("driving_forward")
            else:
                self.actions.add("driving_backward")
        
        # 2. TURN CLASSIFICATION (left/right)
        if abs(self.angular_vel) > ANGULAR_THRESH:
            if self.angular_vel > 0:
                self.actions.add("turning_left")
            else:
                self.actions.add("turning_right")
        
        # 3. ATTACHMENT CLASSIFICATION (for each motor independently)
        for port, vel in self.attachment_vels.items():
            if abs(vel) > ATTACHMENT_THRESH:
                if vel > 0:
                    self.actions.add(f"attachment_{port}_up")
                else:
                    self.actions.add(f"attachment_{port}_down")
        
        # Default if no motion
        if not self.actions:
            self.actions.add("idle")
        
        return self.actions

def compute_kinematics(data: List[DataPoint], config=None) -> List[KinematicState]:
    """
    Compute kinematic state at each time point using vector analysis
    """
    if len(data) < 2:
        return []
    
    states = []
    
    # Identify drive motors from config
    left_motor = None
    right_motor = None
    attachment_motors = []
    
    if config and "motors" in config:
        for port, role in config["motors"].items():
            if role == "left_drive":
                left_motor = port
            elif role == "right_drive":
                right_motor = port
            elif role == "attachment":
                attachment_motors.append(port)
    
    # Fallback
    if not left_motor or not right_motor:
        left_motor = "A"
        right_motor = "B"
    
    yaw_unwrapped = unwrap_angles([d.yaw for d in data])
    
    for i in range(len(data)):
        state = KinematicState(data[i].t)
        
        if i == 0:
            # First point - no velocity yet
            state.left_vel = 0
            state.right_vel = 0
        else:
            dt_sec = (data[i].t - data[i-1].t) / 1000.0
            if dt_sec > 0:
                # Compute motor velocities (deg/sec)
                left_key = f"motor{left_motor}_rel_deg"
                right_key = f"motor{right_motor}_rel_deg"
                
                if left_key in data[i].motors and left_key in data[i-1].motors:
                    left_delta = data[i].motors[left_key] - data[i-1].motors[left_key]
                    state.left_vel = left_delta / dt_sec
                
                if right_key in data[i].motors and right_key in data[i-1].motors:
                    right_delta = data[i].motors[right_key] - data[i-1].motors[right_key]
                    state.right_vel = right_delta / dt_sec
                
                # Attachment motor velocities
                for port in attachment_motors:
                    att_key = f"motor{port}_rel_deg"
                    if att_key in data[i].motors and att_key in data[i-1].motors:
                        att_delta = data[i].motors[att_key] - data[i-1].motors[att_key]
                        state.attachment_vels[port] = att_delta / dt_sec
            
            # Power levels (normalized 0-1 based on velocity)
            MAX_VEL = 180.0  # deg/sec max
            state.left_power = min(1.0, abs(state.left_vel) / MAX_VEL)
            state.right_power = min(1.0, abs(state.right_vel) / MAX_VEL)
        
        # Classify actions at this moment
        state.classify()
        states.append(state)
    
    return states

# ============================================================
# SEGMENT GENERATION - Merge consecutive similar states
# ============================================================

def generate_segments(states: List[KinematicState], min_duration_ms=150) -> List[Dict]:
    """
    Convert kinematic states into segments where action set remains constant
    """
    if not states:
        return []
    
    segments = []
    current_actions = states[0].actions
    start_idx = 0
    start_time = states[0].t
    
    for i in range(1, len(states)):
        # Check if action set changed
        if states[i].actions != current_actions:
            # Save current segment
            duration = states[i].t - start_time
            
            if duration >= min_duration_ms:
                # Compute average metrics for segment
                segment_states = states[start_idx:i]
                avg_linear = sum(s.linear_vel for s in segment_states) / len(segment_states)
                avg_angular = sum(s.angular_vel for s in segment_states) / len(segment_states)
                
                segment = {
                    'start_ms': start_time,
                    'end_ms': states[i].t,
                    'duration_ms': duration,
                    'actions': sorted(list(current_actions)),  # Sorted for consistency
                    'avg_linear_vel': round(avg_linear, 2),
                    'avg_angular_vel': round(avg_angular, 2),
                    'description': format_segment_description(current_actions)
                }
                segments.append(segment)
            
            # Start new segment
            current_actions = states[i].actions
            start_idx = i
            start_time = states[i].t
    
    # Add final segment
    if len(states) > start_idx:
        duration = states[-1].t - start_time
        if duration >= min_duration_ms:
            segment_states = states[start_idx:]
            avg_linear = sum(s.linear_vel for s in segment_states) / len(segment_states)
            avg_angular = sum(s.angular_vel for s in segment_states) / len(segment_states)
            
            segment = {
                'start_ms': start_time,
                'end_ms': states[-1].t,
                'duration_ms': duration,
                'actions': sorted(list(current_actions)),
                'avg_linear_vel': round(avg_linear, 2),
                'avg_angular_vel': round(avg_angular, 2),
                'description': format_segment_description(current_actions)
            }
            segments.append(segment)
    
    return segments

def format_segment_description(actions: Set[str]) -> str:
    """Create human-readable description of action set"""
    if "idle" in actions:
        return "Idle"
    
    description_parts = []
    
    # Main motion
    if "driving_forward" in actions:
        description_parts.append("Drive Forward")
    elif "driving_backward" in actions:
        description_parts.append("Drive Backward")
    
    # Rotation
    if "turning_left" in actions:
        description_parts.append("Turn Left")
    elif "turning_right" in actions:
        description_parts.append("Turn Right")
    
    # Attachments
    for action in sorted(actions):
        if "attachment" in action:
            if "up" in action:
                port = action.split("_")[1]
                description_parts.append(f"Raise {port}")
            elif "down" in action:
                port = action.split("_")[1]
                description_parts.append(f"Lower {port}")
    
    return " + ".join(description_parts) if description_parts else "Unknown"

# ============================================================
# MAIN ANALYSIS FUNCTION
# ============================================================

def run(csv_path, config=None):
    """
    Analyze movement with proper vector kinematics
    
    Returns:
        tuple: (segments, kinematic_summary)
    """
    print("\nLoading data...")
    data = load_data(csv_path)
    
    if not data:
        return [], {}
    
    print("Computing kinematics...")
    states = compute_kinematics(data, config)
    
    print("Generating segments...")
    segments = generate_segments(states)
    
    # Compute summary statistics
    summary = {
        'total_time_ms': data[-1].t if data else 0,
        'total_segments': len(segments),
        'avg_segment_duration': round(sum(s['duration_ms'] for s in segments) / len(segments), 1) if segments else 0,
        'unique_actions': set(),
    }
    
    for segment in segments:
        summary['unique_actions'].update(segment['actions'])
    
    summary['unique_actions'] = sorted(list(summary['unique_actions']))
    
    return segments, summary

# ============================================================
# MAIN (for testing)
# ============================================================

if __name__ == "__main__":
    INPUT_FILE = Path("backend/data/raw_data.csv")
    
    segments, summary = run(str(INPUT_FILE))
    
    print("\n=== Movement Analysis Results ===")
    print(f"Total time: {summary['total_time_ms']}ms")
    print(f"Total segments: {summary['total_segments']}")
    print(f"Unique actions: {summary['unique_actions']}")
    
    print("\nSegments:")
    for seg in segments:
        print(f"[{seg['start_ms']:.0f} - {seg['end_ms']:.0f}] ({seg['duration_ms']:.0f}ms)")
        print(f"  Actions: {', '.join(seg['actions'])}")
        print(f"  Description: {seg['description']}")
        print(f"  Linear: {seg['avg_linear_vel']:.1f} deg/s, Angular: {seg['avg_angular_vel']:.1f} deg/s")