"""
Title: movement_analysis.py
Course: ICS4U-02
Author: Akshit Erukulla & Rick He
Summary: 
- Analyzes recorded robot motor CSV data and segments motion into labeled actions such as driving, turning, arm movement, and idle.
- Outputs a segments.json file that can be used for semantic replay and visualization.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict

def load_csv_data(csv_path):
    """
    Loads motor relative position values from a CSV log into a list of frame dictionaries.
    Each frame contains a timestamp and motor positions for ports A, B, and C.

    Args:
        csv_path (str): Path to the CSV log file.

    Returns:
        list[dict]: List of frames containing time_ms and motor position values.
    """
    frames = []
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                time_ms = int(float(row.get('time_ms', 0)))
                motors = {}
                for port in ['A', 'B', 'C']:
                    rel_key = f'motor{port}_rel_deg'
                    motors[port] = float(row.get(rel_key, 0))
                
                frames.append({
                    'time_ms': time_ms,
                    'motors': motors
                })
            except:
                pass
    return frames

def calculate_velocities(frames):
    """
    Loads motor relative position values from a CSV log into a list of frame dictionaries.
    Each frame contains a timestamp and motor positions for ports A, B, and C.

    Args:
        csv_path (str): Path to the CSV log file.

    Returns:
        list[dict]: List of frames containing time_ms and motor position values.
    """
    velocities = []
    
    for i in range(1, len(frames)):
        curr = frames[i]
        prev = frames[i-1]
        dt_ms = max(1, curr['time_ms'] - prev['time_ms'])
        dt_sec = dt_ms / 1000.0
        
        frame_vel = {}
        for port in ['A', 'B', 'C']:
            delta = curr['motors'][port] - prev['motors'][port]
            vel_deg_per_sec = delta / dt_sec  # Keep sign for direction!
            frame_vel[port] = vel_deg_per_sec
        
        velocities.append(frame_vel)
    
    return velocities

def segment_movements(frames, velocities, velocity_threshold=2.0):
    """
    Loads motor relative position values from a CSV log into a list of frame dictionaries.
    Each frame contains a timestamp and motor positions for ports A, B, and C.

    Args:
        csv_path (str): Path to the CSV log file.

    Returns:
        list[dict]: List of frames containing time_ms and motor position values.
    """
    segments = []
    current_segment = None
    
    for i in range(len(velocities)):
        frame_idx = i + 1
        frame = frames[frame_idx]
        vel = velocities[i]
        
        # Any motor moving above threshold = moving
        is_moving = any(abs(v) > velocity_threshold for v in vel.values())
        
        if not current_segment:
            current_segment = {
                'start_idx': frame_idx,
                'start_ms': frame['time_ms'],
                'end_ms': frame['time_ms'],  # FIXED: Initialize end_ms
                'is_moving': is_moving,
                'motor_A': [],
                'motor_B': [],
                'motor_C': []
            }
        
        # Collect velocities for each motor
        if abs(vel['A']) > velocity_threshold:
            current_segment['motor_A'].append(vel['A'])
        if abs(vel['B']) > velocity_threshold:
            current_segment['motor_B'].append(vel['B'])
        if abs(vel['C']) > velocity_threshold:
            current_segment['motor_C'].append(vel['C'])
        
        # Update end_ms
        current_segment['end_ms'] = frame['time_ms']
        
        # Check for segment boundary (movement state change)
        if is_moving != current_segment['is_moving']:
            # Save this segment
            if current_segment['end_ms'] > current_segment['start_ms']:
                segments.append(current_segment)
            
            # Start new segment
            current_segment = {
                'start_idx': frame_idx,
                'start_ms': frame['time_ms'],
                'end_ms': frame['time_ms'],  # FIXED: Initialize end_ms
                'is_moving': is_moving,
                'motor_A': [],
                'motor_B': [],
                'motor_C': []
            }
    
    # Don't forget the final segment
    if current_segment and current_segment['end_ms'] >= current_segment['start_ms']:
        segments.append(current_segment)
    
    return segments

def classify_segment(segment):
    """
    Loads motor relative position values from a CSV log into a list of frame dictionaries.
    Each frame contains a timestamp and motor positions for ports A, B, and C.

    Args:
        csv_path (str): Path to the CSV log file.

    Returns:
        list[dict]: List of frames containing time_ms and motor position values.
    """
    
    # Get movement data for each motor
    motor_a_vels = segment.get('motor_A', [])
    motor_b_vels = segment.get('motor_B', [])
    motor_c_vels = segment.get('motor_C', [])
    
    # If no motion, it's idle
    if not motor_a_vels and not motor_b_vels and not motor_c_vels:
        return "Idle"
    
    # Classify drive motors (A and B)
    drive_desc = classify_drive(motor_a_vels, motor_b_vels)
    
    # Classify arm motor (C)
    arm_desc = classify_arm(motor_c_vels)
    
    # Combine descriptions
    if drive_desc and arm_desc:
        return f"{drive_desc} + {arm_desc}"
    elif drive_desc:
        return drive_desc
    elif arm_desc:
        return arm_desc
    else:
        return "Idle"

def classify_drive(motor_a_vels, motor_b_vels):
    """
    Loads motor relative position values from a CSV log into a list of frame dictionaries.
    Each frame contains a timestamp and motor positions for ports A, B, and C.

    Args:
        csv_path (str): Path to the CSV log file.

    Returns:
        list[dict]: List of frames containing time_ms and motor position values.
    """
    
    if not motor_a_vels and not motor_b_vels:
        return None
    
    # Calculate average velocities (keeping sign for direction)
    avg_a = sum(motor_a_vels) / len(motor_a_vels) if motor_a_vels else 0
    avg_b = sum(motor_b_vels) / len(motor_b_vels) if motor_b_vels else 0
    
    # Magnitude (absolute)
    mag_a = abs(avg_a)
    mag_b = abs(avg_b)
    
    # Check if we have actual movement
    if mag_a < 0.5 and mag_b < 0.5:
        return None
    
    # Determine movement type
    # If motors move together (similar direction and magnitude), it's straight
    # If motors move opposite (opposite direction or very different magnitude), it's a turn
    
    # Calculate difference
    diff = abs(mag_a - mag_b)
    total = mag_a + mag_b
    ratio = diff / total if total > 0 else 0
    
    # If ratio > 0.3, it's a turn (motors significantly different)
    # If ratio < 0.3, it's straight movement (motors similar)
    
    if ratio > 0.3:
        # Turn movement
        if mag_a > mag_b:
            return "Turn Left"
        else:
            return "Turn Right"
    else:
        # Straight movement - determine forward or backward
        # Use sign of the larger velocity
        if mag_a >= mag_b:
            if avg_a > 0:
                return "Drive Backward"  # Motor A forward = robot backward
            else:
                return "Drive Forward"   # Motor A backward = robot forward
        else:
            if avg_b > 0:
                return "Drive Backward"  # Motor B forward = robot backward
            else:
                return "Drive Forward"   # Motor B backward = robot forward

def classify_arm(motor_c_vels):
    """
    Loads motor relative position values from a CSV log into a list of frame dictionaries.
    Each frame contains a timestamp and motor positions for ports A, B, and C.

    Args:
        csv_path (str): Path to the CSV log file.

    Returns:
        list[dict]: List of frames containing time_ms and motor position values.
    """
    
    if not motor_c_vels:
        return None
    
    # Calculate average velocity
    avg_c = sum(motor_c_vels) / len(motor_c_vels)
    
    if abs(avg_c) < 0.5:
        return None
    
    if avg_c > 0:
        return "Raise Arm"
    else:
        return "Lower Arm"

def merge_consecutive_idle_segments(segments):
    """
    Loads motor relative position values from a CSV log into a list of frame dictionaries.
    Each frame contains a timestamp and motor positions for ports A, B, and C.

    Args:
        csv_path (str): Path to the CSV log file.

    Returns:
        list[dict]: List of frames containing time_ms and motor position values.
    """
    if not segments:
        return segments
    
    merged = []
    current = None
    
    for seg in segments:
        if current is None:
            current = seg.copy()
        elif seg['description'] == 'Idle' and current['description'] == 'Idle':
            # Extend current segment to include this idle
            current['end_ms'] = seg['end_ms']
            current['duration_ms'] = current['end_ms'] - current['start_ms']
        else:
            # Save current and start new
            merged.append(current)
            current = seg.copy()
    
    if current:
        merged.append(current)
    
    return merged

def run(csv_path='backend/data/raw_data.csv', output_path='backend/data/segments.json'):
    """
    Loads motor relative position values from a CSV log into a list of frame dictionaries.
    Each frame contains a timestamp and motor positions for ports A, B, and C.

    Args:
        csv_path (str): Path to the CSV log file.

    Returns:
        list[dict]: List of frames containing time_ms and motor position values.
    """
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        print(f"ERROR: {csv_file} not found")
        return False
    
    try:
        print(f"[*] Loading CSV: {csv_file}")
        frames = load_csv_data(str(csv_file))
        print(f"[OK] Loaded {len(frames)} frames")
        
        if len(frames) < 2:
            print("[ERROR] Not enough frames")
            return False
        
        print("[*] Calculating velocities...")
        velocities = calculate_velocities(frames)
        
        print("[*] Segmenting movements...")
        segments = segment_movements(frames, velocities, velocity_threshold=2.0)
        print(f"[OK] Found {len(segments)} raw segments")
        
        print("[*] Classifying segments...")
        segments_with_desc = []
        for i, seg in enumerate(segments, 1):
            # FIXED: Validate segment has required fields
            if 'start_ms' not in seg or 'end_ms' not in seg:
                print(f"[WARNING] Segment {i} missing start_ms or end_ms, skipping")
                continue
                
            description = classify_segment(seg)
            duration_ms = seg['end_ms'] - seg['start_ms']
            
            segments_with_desc.append({
                'index': i,
                'description': description,
                'start_ms': seg['start_ms'],
                'end_ms': seg['end_ms'],
                'duration_ms': duration_ms
            })
        
        print(f"[OK] Classified {len(segments_with_desc)} segments")
        
        print("[*] Merging consecutive idle segments...")
        segments_merged = merge_consecutive_idle_segments(segments_with_desc)
        print(f"[OK] After merge: {len(segments_merged)} segments")
        
        # Re-index after merge
        for i, seg in enumerate(segments_merged, 1):
            seg['index'] = i
        
        # Display results
        print("\n" + "=" * 100)
        print("MOVEMENT SEGMENTS:")
        print("=" * 100)
        for seg in segments_merged:
            print(f"[{seg['index']:2d}] {seg['description']:40s} {seg['start_ms']:5d}ms - {seg['end_ms']:5d}ms ({seg['duration_ms']:4d}ms)")
        print("=" * 100)
        
        # Save to JSON - resolve to absolute path and force flush
        import os as _os
        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_file.exists():
            print(f"[DEBUG] Deleting old file: {output_file}")
            output_file.unlink()

        json_str = json.dumps(segments_merged, indent=2)
        print(f"[DEBUG] Writing {len(segments_merged)} segments to {output_file}")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_str)
            f.flush()
            _os.fsync(f.fileno())

        if not output_file.exists():
            print(f"[ERROR] File not found after write: {output_file}")
            return False

        written_size = output_file.stat().st_size
        print(f"[OK] Saved to {output_file} ({written_size} bytes)\n")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run()
