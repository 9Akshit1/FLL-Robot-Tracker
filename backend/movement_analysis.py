#!/usr/bin/env python3
"""
Movement Analysis - FINAL VERSION
- Has run() function for dashboard
- Merges consecutive idle segments
- Classifies combined movements (Drive + Arm)
- Ignores minor turns (turn_ratio < 0.2)
"""

import csv
import json
from pathlib import Path
from collections import defaultdict

def load_csv_data(csv_path):
    """Load motor data from CSV"""
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
    """Calculate motor velocities (degrees per second)"""
    velocities = []
    
    for i in range(1, len(frames)):
        curr = frames[i]
        prev = frames[i-1]
        dt_ms = max(1, curr['time_ms'] - prev['time_ms'])
        
        frame_vel = {}
        for port in ['A', 'B', 'C']:
            delta = curr['motors'][port] - prev['motors'][port]
            vel_deg_per_sec = abs(delta) / (dt_ms / 1000.0)
            frame_vel[port] = vel_deg_per_sec
        
        velocities.append(frame_vel)
    
    return velocities

def segment_movements(frames, velocities, velocity_threshold=2.0):
    """Segment movements based on velocity changes"""
    segments = []
    current_segment = None
    
    for i in range(len(velocities)):
        frame_idx = i + 1
        frame = frames[frame_idx]
        vel = velocities[i]
        
        is_moving = any(v > velocity_threshold for v in vel.values())
        
        if not current_segment:
            current_segment = {
                'start_idx': frame_idx,
                'start_ms': frame['time_ms'],
                'is_moving': is_moving,
                'motors': defaultdict(list)
            }
        
        for port in ['A', 'B', 'C']:
            if vel[port] > velocity_threshold:
                current_segment['motors'][port].append(vel[port])
        
        if is_moving != current_segment['is_moving']:
            current_segment['end_idx'] = frame_idx
            current_segment['end_ms'] = frame['time_ms']
            segments.append(current_segment)
            
            current_segment = {
                'start_idx': frame_idx,
                'start_ms': frame['time_ms'],
                'is_moving': is_moving,
                'motors': defaultdict(list)
            }
        else:
            current_segment['end_idx'] = frame_idx
            current_segment['end_ms'] = frame['time_ms']
    
    if current_segment and current_segment['end_ms'] > current_segment['start_ms']:
        segments.append(current_segment)
    
    return segments

def classify_segment(segment):
    """
    IMPROVED: Classify segment with combined movements
    Can output: "Drive Forward + Raise Arm", "Turn Left + Lower Arm", etc.
    """
    motor_a_vel = sum(segment.get('motors', {}).get('A', []))
    motor_b_vel = sum(segment.get('motors', {}).get('B', []))
    motor_c_vel = sum(segment.get('motors', {}).get('C', []))
    
    # Thresholds
    drive_threshold = 50    # Need 50+ deg/sec combined to count as driving
    arm_threshold = 30      # Need 30+ deg/sec to count as arm movement
    
    # Check what's moving significantly
    has_drive = (abs(motor_a_vel) + abs(motor_b_vel)) > drive_threshold
    has_arm = abs(motor_c_vel) > arm_threshold
    
    if not has_drive and not has_arm:
        return "Idle"
    
    # Classify drive direction
    drive_desc = None
    if has_drive:
        a_mag = abs(motor_a_vel)
        b_mag = abs(motor_b_vel)
        total_drive = a_mag + b_mag
        
        # Check turn ratio
        diff = abs(a_mag - b_mag)
        turn_ratio = diff / total_drive if total_drive > 0 else 0
        
        # Only label as turn if >20% difference
        if turn_ratio < 0.2:
            # Straight movement - determine forward or backward
            # Check first velocity direction
            first_a = segment.get('motors', {}).get('A', [None])[0]
            first_b = segment.get('motors', {}).get('B', [None])[0]
            
            if first_a is not None and first_a > 0:
                drive_desc = "Drive Backward"  # A forward = backward direction (convention)
            elif first_b is not None and first_b > 0:
                drive_desc = "Drive Backward"
            else:
                drive_desc = "Drive Forward"
        else:
            # Significant turn
            drive_desc = "Turn Left" if a_mag > b_mag else "Turn Right"
    
    # Classify arm direction
    arm_desc = None
    if has_arm:
        if motor_c_vel > 0:
            arm_desc = "Raise Arm"
        else:
            arm_desc = "Lower Arm"
    
    # Combine classifications
    if drive_desc and arm_desc:
        return f"{drive_desc} + {arm_desc}"
    elif drive_desc:
        return drive_desc
    elif arm_desc:
        return arm_desc
    else:
        return "Idle"

def merge_consecutive_idle_segments(segments):
    """Merge consecutive idle segments into single segments"""
    if not segments:
        return segments
    
    merged = []
    current = None
    
    for seg in segments:
        if current is None:
            current = seg.copy()
        elif seg['description'] == 'Idle' and current['description'] == 'Idle':
            # Extend current segment
            current['end_ms'] = seg['end_ms']
            current['duration_ms'] = current['end_ms'] - current['start_ms']
        else:
            # Save and start new
            merged.append(current)
            current = seg.copy()
    
    if current:
        merged.append(current)
    
    return merged

def run(csv_path='backend/data/raw_data.csv', output_path='backend/data/segments.json'):
    """
    MAIN FUNCTION - Called by dashboard
    Analyzes CSV and generates segments.json
    """
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        print(f"ERROR: {csv_file} not found")
        return False
    
    print(f"[*] Loading CSV: {csv_file}")
    frames = load_csv_data(str(csv_file))
    print(f"[OK] Loaded {len(frames)} frames")
    
    if len(frames) < 2:
        print("[ERROR] Not enough frames")
        return False
    
    print("[*] Calculating velocities...")
    velocities = calculate_velocities(frames)
    
    print("[*] Segmenting movements...")
    segments = segment_movements(frames, velocities)
    print(f"[OK] Found {len(segments)} raw segments")
    
    print("[*] Classifying segments...")
    segments_with_desc = []
    for i, seg in enumerate(segments, 1):
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
    print("\n" + "=" * 90)
    print("MOVEMENT SEGMENTS:")
    print("=" * 90)
    for seg in segments_merged:
        print(f"[{seg['index']:2d}] {seg['description']:40s} {seg['start_ms']:5d}ms - {seg['end_ms']:5d}ms ({seg['duration_ms']:4d}ms)")
    print("=" * 90)
    
    # Save to JSON
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(segments_merged, f, indent=2)
    print(f"[OK] Saved to {output_file}\n")
    
    return True

if __name__ == "__main__":
    run()