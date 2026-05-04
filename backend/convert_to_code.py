# ============================================================
# convert_to_code.py - Kid-Friendly Pybricks Code Generation
# ============================================================

import csv
from typing import List, Dict, Tuple
import os
from pathlib import Path
import json

def load_rows(csv_path, config=None):
    """Load CSV data with dynamic motor support"""
    rows = []

    try:
        with open(csv_path, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            
            if not reader.fieldnames:
                print("ERROR: CSV has no headers")
                return [], {}
            
            reader.fieldnames = [name.replace("\ufeff", "").strip() for name in reader.fieldnames]
            print("Clean headers:", reader.fieldnames)

            for r in reader:
                if not r.get("time_ms") or str(r.get("time_ms", "")).strip().startswith('#'):
                    continue

                try:
                    row = {'t': int(float(r['time_ms']))}
                    
                    motor_roles = {}
                    if config and "motors" in config:
                        for port, role in config["motors"].items():
                            if role:
                                motor_roles[port] = role
                    
                    # Extract motor data
                    for key, val in r.items():
                        if "_rel_deg" in key:
                            try:
                                motor_letter = key.split('motor')[1][0].upper()
                                row[f'{motor_letter}_rel'] = int(float(val))
                            except (IndexError, ValueError):
                                continue

                    rows.append(row)
                except (ValueError, TypeError, KeyError):
                    continue
    except Exception as e:
        print(f"ERROR loading CSV: {e}")
        return [], {}

    print(f"Loaded {len(rows)} rows")
    return rows, motor_roles if config else {}

def compute_speed(deg, dt_ms):
    """Compute motor speed (0-1000 range)"""
    if dt_ms <= 0 or deg == 0:
        return 0
    speed = int((abs(deg) / dt_ms) * 1000)
    return max(100, min(1000, speed))

def generate_motion_commands(rows, config=None) -> List[Tuple]:
    """
    Convert CSV rows into semantic motion commands
    
    Returns list of (time_ms, left_deg, right_deg, attachments_dict)
    """
    if not rows or len(rows) < 2:
        return []
    
    commands = []
    prev = rows[0].copy()
    
    # Get motor assignment from config
    left_motor = "A"
    right_motor = "B"
    attachment_motors = []
    
    if config and "motors" in config:
        for port, role in config["motors"].items():
            if role == "left_drive":
                left_motor = port
            elif role == "right_drive":
                right_motor = port
            elif role == "attachment":
                attachment_motors.append(port)
    
    # Build command sequence
    for r in rows[1:]:
        dt = r['t'] - prev['t']
        
        if dt <= 0:
            prev = r.copy()
            continue
        
        # Calculate motor deltas
        left_delta = r.get(f'{left_motor}_rel', 0) - prev.get(f'{left_motor}_rel', 0)
        right_delta = r.get(f'{right_motor}_rel', 0) - prev.get(f'{right_motor}_rel', 0)
        
        # Attachments
        attachments = {}
        for port in attachment_motors:
            att_delta = r.get(f'{port}_rel', 0) - prev.get(f'{port}_rel', 0)
            if att_delta != 0:
                attachments[port] = att_delta
        
        command = (dt, left_delta, right_delta, attachments)
        commands.append(command)
        prev = r.copy()
    
    return commands

def generate_spike_script(csv_path, out_path, config=None):
    """
    Generate FLL-style readable code with semantic functions
    """
    rows, motor_roles = load_rows(csv_path, config)
    
    if not rows or len(rows) < 2:
        raise RuntimeError("Not enough data loaded from CSV")
    
    commands = generate_motion_commands(rows, config)
    
    if not commands:
        raise RuntimeError("No motion commands generated")
    
    # Get motor ports from config
    left_motor = "A"
    right_motor = "B"
    attachment_motors = []
    
    if config and "motors" in config:
        for port, role in config["motors"].items():
            if role == "left_drive":
                left_motor = port
            elif role == "right_drive":
                right_motor = port
            elif role == "attachment":
                attachment_motors.append(port)
    
    # Generate helper functions for semantic movements
    helper_functions = f"""
# Motor setup
left_motor = port.{left_motor}
right_motor = port.{right_motor}
"""
    
    if attachment_motors:
        for motor in attachment_motors:
            helper_functions += f"attachment_{motor} = port.{motor}\n"
    
    helper_functions += """
# Helper function to calculate motor speed
def get_speed(degrees, time_ms):
    if time_ms <= 0 or degrees == 0:
        return 0
    speed = int((abs(degrees) / time_ms) * 1000)
    return max(100, min(1000, speed))

# Semantic movement functions
def move_forward(distance_deg, speed=500):
    '''Drive robot forward'''
    motor.run_for_degrees(left_motor, distance_deg, speed)
    motor.run_for_degrees(right_motor, distance_deg, speed)

def move_backward(distance_deg, speed=500):
    '''Drive robot backward'''
    motor.run_for_degrees(left_motor, -distance_deg, speed)
    motor.run_for_degrees(right_motor, -distance_deg, speed)

def turn_left(angle_deg, speed=400):
    '''Turn robot left in place'''
    motor.run_for_degrees(left_motor, -angle_deg, speed)
    motor.run_for_degrees(right_motor, angle_deg, speed)

def turn_right(angle_deg, speed=400):
    '''Turn robot right in place'''
    motor.run_for_degrees(left_motor, angle_deg, speed)
    motor.run_for_degrees(right_motor, -angle_deg, speed)

def move_custom(left_deg, right_deg, speed=500):
    '''Move with different speeds on each side (for curves)'''
    motor.run_for_degrees(left_motor, left_deg, speed)
    motor.run_for_degrees(right_motor, right_deg, speed)
"""
    
    if attachment_motors:
        for motor in attachment_motors:
            helper_functions += f"""
def raise_{motor.lower()}(degrees=90, speed=500):
    '''Raise attachment on motor {motor}'''
    motor.run_for_degrees(attachment_{motor}, degrees, speed)

def lower_{motor.lower()}(degrees=90, speed=500):
    '''Lower attachment on motor {motor}'''
    motor.run_for_degrees(attachment_{motor}, -degrees, speed)
"""
    
    # Generate replay function by analyzing movement patterns
    replay_commands = []
    
    for dt, left_deg, right_deg, attachments in commands:
        speed = max(
            compute_speed(left_deg, dt),
            compute_speed(right_deg, dt)
        ) if (left_deg or right_deg) else 500
        
        # Classify movement for semantic function call
        forward_deg = (left_deg + right_deg) / 2
        turn_deg = (right_deg - left_deg) / 2
        
        command_lines = []
        
        # Determine best semantic function
        if abs(turn_deg) > 3 and abs(forward_deg) < 5:
            # Pure turn
            if turn_deg > 0:
                command_lines.append(f"turn_left({abs(int(turn_deg))}, {speed})")
            else:
                command_lines.append(f"turn_right({abs(int(turn_deg))}, {speed})")
        
        elif abs(forward_deg) > 5:
            # Forward or backward
            if forward_deg > 0:
                command_lines.append(f"move_forward({int(forward_deg)}, {speed})")
            else:
                command_lines.append(f"move_backward({abs(int(forward_deg))}, {speed})")
        
        elif left_deg != 0 or right_deg != 0:
            # Custom mixed motion
            command_lines.append(f"move_custom({int(left_deg)}, {int(right_deg)}, {speed})")
        
        # Add attachment commands
        for port, att_deg in attachments.items():
            att_speed = compute_speed(att_deg, dt)
            if att_deg > 0:
                command_lines.append(f"raise_{port.lower()}({int(att_deg)}, {att_speed})")
            else:
                command_lines.append(f"lower_{port.lower()}({abs(int(att_deg))}, {att_speed})")
        
        replay_commands.extend(command_lines)
    
    # Build final script
    replay_code = '\n    '.join(replay_commands)
    
    script_content = f"""import runloop
import motor
from hub import port

{helper_functions}

async def main():
    '''Main replay routine'''
    print("Starting replay...")
    
    # Execute recorded movements
    {replay_code}
    
    print("Done!")

# Run the program
runloop.run(main())
"""

    with open(out_path, "w") as f:
        f.write(script_content)

    print(f"Script generated: {out_path}")
    return out_path

if __name__ == "__main__":
    INPUT_CSV = Path("backend/data/raw_data.csv")
    OUTPUT_SCRIPT = Path("backend/data/replay.py")

    path = generate_spike_script(str(INPUT_CSV), str(OUTPUT_SCRIPT), config=None)
    print(f"Replay script generated: {path}")