# TESTING_GUIDE.md

## Overview

This guide covers how to test the FLL Robot Tracker for bugs, crashes, and edge cases. Testing happens at three levels:

1. **Unit Tests** - Individual functions (automated)
2. **Integration Tests** - Full workflows (automated)
3. **Manual Testing** - Real scenarios (done by you)

---

## Running Automated Tests

### Setup

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
# View: htmlcov/index.html
```

### Test Categories

```bash
# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run slow tests (takes longer)
pytest tests/ -m slow

# Skip slow tests
pytest tests/ -m "not slow"

# Run a specific test
pytest tests/test_movement_analysis.py::TestDataPoint::test_init_basic -v
```

---

## Manual Testing Scenarios

### Scenario 1: Invalid Configuration

**Goal:** Ensure app rejects bad configs

**Test Steps:**

1. Start app
2. Click "Detect Ports" (should show ports)
3. Try to "Save & Upload Config" without:
   - Selecting a COM port → Should error: "Please select a COM port"
   - Selecting any motor → Should error: "Please select at least one motor"
   - Valid motor/sensor combo → Should succeed

**Expected:** All invalid cases show error messages

**Break It:** Try these deliberately
- Leave COM port as "-- Select Port --"
- Select only "None" for all ports
- Select a port that doesn't exist

---

### Scenario 2: Missing Robot Connection

**Goal:** Graceful handling when robot disconnects

**Test Steps:**

1. Configure robot properly
2. Click "Connect & Record"
3. Immediately unplug USB cable (don't wait for it to finish)
4. Watch for error message (should appear in 10-15 seconds)
5. Plug USB back in
6. Try again (should work)

**Expected:**
- App shows error: "Failed to execute" or similar
- No crash
- Can retry without restarting server

**Terminal Check:**
```bash
python app.py
# Watch for "mpremote timeout" messages
```

---

### Scenario 3: Corrupt or Missing CSV

**Goal:** Handle bad data gracefully

**Test Steps:**

1. Manually create a broken CSV:
   ```bash
   # Linux/Mac
   echo "invalid,data,here" > backend/data/raw_data.csv
   
   # Windows
   echo invalid,data,here > backend\data\raw_data.csv
   ```

2. Click "Analyze" → Should error with "Failed to parse" or similar
3. Delete the CSV file entirely
4. Click "Analyze" → Should error with "No CSV file"
5. Click "Convert" → Should error with "No CSV file"

**Expected:**
- Clear error messages
- No Python stack trace visible to user
- App doesn't crash

---

### Scenario 4: Rapid Button Clicks

**Goal:** Prevent race conditions and duplicate uploads

**Test Steps:**

1. Configure robot
2. Click "Connect & Record" button
3. Immediately click it 5 more times (spam)
4. Wait for first one to finish
5. Try clicking other buttons during operation

**Expected:**
- Only one operation runs at a time
- Second clicks are ignored (button disabled)
- No duplicate uploads to robot

**Check Terminal:**
- Should not see "mpremote" command run twice simultaneously

---

### Scenario 5: Large CSV Files

**Goal:** Handle memory efficiently with big data

**Test Steps:**

1. Create large CSV file
2. Run "Analyze" on it
3. Run "Convert" on it
4. Monitor memory usage:
   ```bash
   # Linux/Mac
   ps aux | grep python
   
   # Windows Task Manager
   ```

5. Try downloading the generated script

**Expected:**
- Completes in reasonable time (< 5 seconds)
- Memory doesn't balloon above 500MB
- Generated script works

---

### Scenario 6: Network Failures (Simulation)

**Goal:** Graceful handling of timeouts

**Test Steps:**

1. Configure robot correctly
2. **Simulate slow network:**
   - Windows: Use NetLimiter or TMeter
   - Mac: Network Link Conditioner
   - Linux: `tc` command

3. Click "Connect & Record" with slow network
4. Observe timeout handling (should timeout after 10 min, not hang forever)

**Expected:**
- Clear timeout message after reasonable delay
- App remains responsive
- Can retry

---

### Scenario 7: Port Permission Errors (Linux/Mac)

**Goal:** Handle serial port permission issues

**Test Steps (Linux):**

```bash
# Simulate permission error
sudo chmod 000 /dev/ttyUSB0

# Try to detect ports
python app.py  # Browser: click "Detect Ports"

# Restore permissions
sudo chmod 666 /dev/ttyUSB0
```

**Expected:**
- Show "Permission denied" error
- Suggest user solution: `sudo usermod -a -G dialout $USER`

---

### Scenario 8: Disk Space Issues

**Goal:** Handle low disk space

**Test Steps (Linux/Mac):**

1. Fill your disk almost completely:
   ```bash
   # Create large temp file
   dd if=/dev/zero of=filler bs=1M count=1000
   ```

2. Try to record and analyze data
3. Watch for error when writing CSV

**Expected:**
- Clear "Disk space" error
- Suggestion to free up space

---

### Scenario 9: Concurrent Requests

**Goal:** Handle multiple users/tabs

**Test Steps:**

1. Open app in 2 browser tabs
2. In Tab 1: Click "Connect & Record"
3. In Tab 2: While recording, click "Pull CSV"
4. Observe behavior

**Expected:**
- Requests queued or rejected with error
- No data corruption
- Tab 1 continues normally

**Better fix:** Add locking in `app.py`:
```python
import threading
operation_lock = threading.Lock()

@app.route("/connect")
def connect():
    if not operation_lock.acquire(blocking=False):
        return jsonify({"error": "Operation in progress"}), 429
    try:
        # ... do work ...
    finally:
        operation_lock.release()
```

---

### Scenario 10: Invalid CSV Format

**Goal:** Handle various malformed CSVs

**Test Steps:**

1. Create CSV missing columns:
   ```
   time_ms,motorA_rel_deg
   0,45
   ```
   Missing all other columns. Click "Analyze" → Should handle gracefully

2. Create CSV with wrong data types:
   ```
   time_ms,motorA_rel_deg
   abc,def
   ```
   Click "Analyze" → Should skip bad rows

3. Create CSV with Unicode issues:
   ```
   time_ms,🎯_deg
   0,45
   ```
   Click "Analyze" → Should handle or skip

**Expected:**
- No crashes
- Helpful error messages
- Can skip bad data and continue

---

## Common Issues to Look For

### 1. Memory Leaks

```bash
# Run app, monitor memory
while true; do ps aux | grep python; sleep 1; done

# Click buttons repeatedly
# Memory should stay ~100-150MB, not grow to 1GB
```

### 2. File Handle Leaks

```python
# Check if files closed properly
import psutil
p = psutil.Process()
p.open_files()  # Should be small number
```

### 3. Zombie Processes

```bash
ps aux | grep defunct
# If you see <defunct>, processes not cleaned up
```

### 4. Race Conditions

Add print statements and check logs:
```python
print(f"[{time.time()}] Starting connect...")
print(f"[{time.time()}] Config: {current_config}")
print(f"[{time.time()}] Uploading code...")
```

---

## Debugging Tools

### Flask Debug Mode
```python
# app.py
app.run(debug=True)  # Enables interactive debugger
```

### Browser DevTools
- F12 to open
- Network tab: See API calls and responses
- Console: Check for JavaScript errors
- Storage: View localStorage (saved config)

### mpremote Debug
```bash
mpremote --help
mpremote connect COM3 ls /flash  # List files on robot
mpremote connect COM3 cat /flash/data_log.csv | head -20  # View CSV
```

---
