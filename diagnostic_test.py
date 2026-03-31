#!/usr/bin/env python3
"""
Diagnostic script to verify hub communication
"""

import subprocess
import time
import sys

SERIAL_PORT = "COM5"

def run_cmd(cmd_list, show_output=True):
    """Run a command and return success/output"""
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=5)
        if show_output:
            print(f"CMD: {' '.join(cmd_list)}")
            print(f"OUTPUT:\n{result.stdout}{result.stderr}")
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        if show_output:
            print(f"ERROR: {e}")
        return False, str(e)

print("\n" + "="*70)
print("HUB DIAGNOSTIC TEST")
print("="*70)

# Test 1: Basic connectivity
print("\n[TEST 1] Basic connectivity")
print("-" * 70)
success, output = run_cmd(["mpremote", "connect", SERIAL_PORT, "exec", "print('HELLO')"])
if not success:
    print("❌ FAILED: Cannot communicate with hub")
    sys.exit(1)
print("✓ Hub is responsive")

# Test 2: Check if variables can be set
print("\n[TEST 2] Setting global variables")
print("-" * 70)
success, output = run_cmd([
    "mpremote", "connect", SERIAL_PORT, "exec",
    "test_var = 42; print('test_var set to:', test_var)"
])
if not success:
    print("❌ FAILED: Cannot set variables")
else:
    print("✓ Variables can be set")

# Test 3: Upload the debugged script
print("\n[TEST 3] Upload produce_data_DEBUGGED.py as main.py")
print("-" * 70)
success, output = run_cmd([
    "mpremote", "connect", SERIAL_PORT, "cp",
    "backend/produce_data.py", ":main.py"
], show_output=False)

if not success:
    print("❌ FAILED: Could not upload produce_data.py")
    print(f"ERROR: {output}")
    sys.exit(1)

print("✓ Script uploaded, waiting for restart...")
time.sleep(3)

# Test 4: Check if hub initialized
print("\n[TEST 4] Verify hub restarted and shows READY")
print("-" * 70)
success, output = run_cmd([
    "mpremote", "connect", SERIAL_PORT, "exec",
    "print('#Hub running, checking for start_flag'); print('start_flag' in dir())"
], show_output=False)

if "True" in output or "start_flag" in output:
    print("✓ Hub script loaded, start_flag exists")
else:
    print("⚠️  Could not verify start_flag exists")
    print(f"Output: {output}")

# Test 5: Try to set start_flag
print("\n[TEST 5] Try to set start_flag = True")
print("-" * 70)
success, output = run_cmd([
    "mpremote", "connect", SERIAL_PORT, "exec",
    "start_flag = True; print('start_flag is now:', start_flag)"
])

if "True" in output:
    print("✓ start_flag was set successfully")
else:
    print("⚠️  Could not verify start_flag was set")

# Test 6: Check hub light matrix
print("\n[TEST 6] What does hub light matrix show?")
print("-" * 70)
print("Check the hub's light matrix display:")
print("  - If it shows 'READY': Script started but not recording")
print("  - If it shows 'REC': Recording is active")
print("  - If it shows 'STOP': Stopped")
print("\nCan you see the light matrix? What does it show?")

# Test 7: Manual recording test
print("\n[TEST 7] Manual recording test")
print("-" * 70)
print("Sending: start_flag = True")
run_cmd([
    "mpremote", "connect", SERIAL_PORT, "exec",
    "start_flag = True"
], show_output=False)

print("⏱️  Move your robot for 3 seconds...")
for i in range(3, 0, -1):
    print(f"   {i}...", end=" ", flush=True)
    time.sleep(1)
print("Done!")

print("\nSending: stop_flag = True")
run_cmd([
    "mpremote", "connect", SERIAL_PORT, "exec",
    "stop_flag = True"
], show_output=False)

time.sleep(2)

# Test 8: Check CSV size
print("\n[TEST 8] Checking CSV size")
print("-" * 70)
success, output = run_cmd([
    "mpremote", "connect", SERIAL_PORT, "fs", "ls", "/flash/data_log.csv"
], show_output=False)

if success and output.strip():
    parts = output.strip().split()
    if parts:
        size = int(parts[0])
        print(f"CSV size: {size} bytes")
        if size > 100:
            print("✓ Data was recorded!")
        else:
            print("⚠️  CSV exists but is too small (< 100 bytes)")
            print("   This usually means recording didn't start or robot didn't move")
else:
    print("❌ Could not read CSV file")

print("\n" + "="*70)
print("DIAGNOSTICS COMPLETE")
print("="*70)
print("\nNext steps:")
print("1. Check what the light matrix shows")
print("2. If it shows READY but never REC: variables not accessible")
print("3. If it shows REC: recording started, but robot might not have moved")
print("4. Try moving the robot more vigorously")
print("\n")