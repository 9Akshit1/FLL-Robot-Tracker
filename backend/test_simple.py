#!/usr/bin/env python3
"""
Simple test for command execution on the hub
No file uploads needed - just execute Python directly
"""

import subprocess
import time
import sys

SERIAL_PORT = "COM5"

def run_cmd(cmd_list):
    """Run a command and return success/output"""
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

print("\n" + "="*60)
print("FLL ROBOT TRACKER - SIMPLE TEST")
print("="*60)
print("\n⚠️  IMPORTANT: Move your robot around during the recording phase!")
print("    The test will record for 5 seconds.\n")

# Step 1: Check connectivity
print("[1/4] Checking hub connectivity...")
success, output = run_cmd(["mpremote", "connect", SERIAL_PORT, "fs", "ls", "/flash/"])
if not success:
    print("❌ Cannot connect to hub. Check COM5.")
    sys.exit(1)
print("✓ Connected to hub")

# Step 2: Get initial CSV size
print("\n[2/4] Starting recording...")
success, output = run_cmd(["mpremote", "connect", SERIAL_PORT, "fs", "ls", "/flash/data_log.csv"])
initial_size = 0
if success:
    parts = output.strip().split()
    if parts:
        initial_size = int(parts[0])

print(f"Initial CSV size: {initial_size} bytes")

# Step 3: Send START command via exec
print("Sending START command...")
success, output = run_cmd([
    "mpremote", "connect", SERIAL_PORT, "exec", 
    "start_flag = True"
])
if not success:
    print(f"⚠️  Could not set start_flag: {output}")
else:
    print("✓ START command sent")

time.sleep(0.5)

# Step 4: Record for 5 seconds while robot moves
print("\n📝 NOW: Move your robot around! Recording for 5 seconds...")
for i in range(5, 0, -1):
    print(f"   {i}...", end=" ", flush=True)
    time.sleep(1)
print("Done!\n")

# Step 5: Send STOP command via exec
print("[3/4] Stopping recording...")
success, output = run_cmd([
    "mpremote", "connect", SERIAL_PORT, "exec",
    "stop_flag = True"
])
if not success:
    print(f"⚠️  Could not set stop_flag: {output}")
else:
    print("✓ STOP command sent")

time.sleep(2)

# Step 6: Check final CSV size
print("\n[4/4] Checking recorded data...")
success, output = run_cmd(["mpremote", "connect", SERIAL_PORT, "fs", "ls", "/flash/data_log.csv"])
final_size = 0
if success:
    parts = output.strip().split()
    if parts:
        final_size = int(parts[0])

data_recorded = final_size - initial_size
print(f"Initial CSV size: {initial_size} bytes")
print(f"Final CSV size: {final_size} bytes")
print(f"Data recorded: {data_recorded} bytes")

print("\n" + "="*60)

if final_size > initial_size and data_recorded > 100:
    print("✅ SUCCESS! Data was recorded!")
    print("\nYou can now use the Flask app:")
    print("  1. Copy app_WORKING.py to backend/app.py")
    print("  2. Copy produce_data_WORKING.py to backend/produce_data.py")
    print("  3. Run: python -m backend.app")
    
    # Try to pull the file
    print("\nPulling CSV to inspect...")
    success, _ = run_cmd([
        "mpremote", "connect", SERIAL_PORT, "cp",
        ":flash/data_log.csv",
        "test_data.csv"
    ])
    
    if success:
        with open("test_data.csv") as f:
            lines = f.readlines()
            print(f"✓ CSV has {len(lines)} lines")
            print(f"  First 3 lines:")
            for line in lines[:3]:
                print(f"    {line.rstrip()}")
else:
    print("❌ FAILED: No data recorded!")
    print("\nTroubleshooting:")
    print("  1. Did you move the robot during the 5 second window?")
    print("  2. Check hub light matrix shows: READY → REC → STOP")
    print("  3. Try re-uploading main.py:")
    print("     mpremote connect COM5 cp backend/produce_data.py :main.py")
    print("  4. Wait 2 seconds for hub to restart")
    print("  5. Run this test again")

print("="*60 + "\n")