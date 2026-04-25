# FLL Robot Tracker - API Reference

## Base URL
```
http://127.0.0.1:5000
```

## Authentication
None required (local only). For production, add token authentication.

---

## Endpoints

### Configuration

#### GET /detect_ports
Scan system for available serial ports.

**Response (200):**
```json
{
  "status": "Success",
  "ports": [
    {
      "port": "COM3",
      "description": "Silicon Labs CP210x USB to UART Bridge Controller"
    },
    {
      "port": "COM4",
      "description": "USB Serial Device"
    }
  ]
}
```

**Error (500):**
```json
{
  "status": "Error",
  "message": "Failed to detect ports",
  "ports": []
}
```

---

#### POST /config
Save robot configuration and upload to hub.

**Request:**
```json
{
  "config": {
    "com_port": "COM3",
    "motors": {
      "A": true,
      "B": true,
      "C": false
    },
    "sensors": {
      "distance": "D",
      "force": "F"
    }
  }
}
```

**Response (200):**
```json
{
  "status": "Config saved",
  "config": {
    "com_port": "COM3",
    "motors": {"A": true, "B": true, "C": false},
    "sensors": {"distance": "D", "force": "F"}
  }
}
```

**Error (400/500):**
```json
{
  "status": "Error",
  "message": "Invalid config"
}
```

**Validation Rules:**
- `com_port` required and must exist
- At least one motor required
- Sensor port letters must be A-F

---

#### GET /config
Retrieve current configuration.

**Response (200):**
```json
{
  "status": "Success",
  "config": {
    "com_port": "COM3",
    "motors": {"A": true, "B": true},
    "sensors": {"distance": "D"}
  }
}
```

---

## Workflow Endpoints

These follow a sequential workflow. Each step depends on the previous one.

### 1. Connect & Record

#### GET /connect
Upload collection code to robot and start recording. Waits for user button press to stop.

**Response (200):**
```json
{
  "status": "Recording complete",
  "message": "Ready to pull data",
  "output": "✓ Code uploaded\n✓ Recording complete"
}
```

**Error (500):**
```json
{
  "status": "Error",
  "message": "Failed to execute",
  "output": "✗ Error:\nUnable to connect to robot"
}
```

**How It Works:**
1. Uploads `collect_data_2_0.py` to robot as `main.py`
2. Executes on robot (waits for button press)
3. LEFT button (or START command): Begin recording
4. RIGHT button (or STOP command): End and save
5. Returns when recording stops

**Timeout:** 10 minutes (allows user time to perform motion)

---

### 2. Pull CSV

#### GET /pull_csv
Download recorded data from robot.

**Response (200):**
```json
{
  "status": "Success",
  "csv_size": 4096,
  "message": "Pulled 4096 bytes",
  "output": "✓ CSV pulled\n✓ Size: 4096 bytes\n✓ Headers: 10 columns",
  "headers": [
    "time_ms",
    "motorA_rel_deg",
    "motorA_abs_deg",
    ...
  ]
}
```

**Error (500):**
```json
{
  "status": "Error",
  "message": "Failed to pull",
  "output": "✗ Could not find CSV"
}
```

**File Location:** `backend/data/raw_data.csv`

---

### 3. Analyze Movement

#### GET /analyze
Analyze CSV to detect movement patterns.

**Response (200):**
```json
{
  "status": "Success",
  "message": "Analysis complete",
  "output": "✓ Analysis complete\n\nDetected Segments:\n[0 - 2500] driving_straight   Speed:  45.23 deg/s Duration: 2.50s\n[2500 - 3200] turning_right    Speed:  23.45 deg/s Duration: 0.70s\n[3200 - 5000] stationary       Speed:   0.00 deg/s Duration: 1.80s"
}
```

**What It Detects:**
- `driving_straight` - Both motors moving, minimal yaw
- `turning_left` - High yaw velocity, positive direction
- `turning_right` - High yaw velocity, negative direction
- `stationary` - Motors not moving

**Thresholds (configurable):**
- Drive threshold: 12 deg/s
- Yaw threshold: 12 deg/s
- Min segment duration: 200ms

---

#### GET /get_segments
Get segments as structured data (useful for visualization).

**Response (200):**
```json
{
  "status": "Success",
  "segments": [
    [0, 2500, "driving_straight"],
    [2500, 3200, "turning_right"],
    [3200, 5000, "stationary"]
  ]
}
```

Format: `[start_ms, end_ms, movement_type]`

---

### 4. Generate Script

#### GET /convert
Convert CSV to Python replay script.

**Response (200):**
```json
{
  "status": "Success",
  "script_size": 2048,
  "message": "Generated (2048 bytes)",
  "output": "✓ Script generated\n✓ Size: 2048 bytes",
  "script_content": "import runloop\nimport motor\nfrom hub import port\n\ntimeline = [\n  (150, 45, 45),\n  (150, 45, 45),\n  ...\n]\n\nasync def main():\n    for motion in timeline:\n        await move_motors(*motion)\n    print(\"Replay complete\")\n\nrunloop.run(main())"
}
```

**Output File Location:** `backend/data/generated_script.py`

**Script Format:**
```python
timeline = [
  (dt_ms, motor_A_delta_deg, motor_B_delta_deg, motor_C_delta_deg),
  ...
]
```

---

### 5. Upload & Run

#### GET /upload_script
Upload generated script to robot.

**Response (200):**
```json
{
  "status": "Success",
  "message": "Script uploaded",
  "output": "✓ Script uploaded\n✓ Ready to run"
}
```

**Error (500):**
```json
{
  "status": "Error",
  "message": "Upload failed",
  "output": "✗ Upload failed"
}
```

**File Location on Robot:** `/flash/replay.py`

---

#### GET /run_script
Execute replay script on robot.

**Response (200):**
```json
{
  "status": "Success",
  "message": "Script completed",
  "output": "✓ Script ran\n\nReplay complete"
}
```

**Timeout:** 5 minutes

**Note:** Watch your robot! The replay will execute immediately and should reproduce the original motion.

---

## Data Formats

### CSV Structure
Dynamically generated based on config. Example:

```
time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,motorC_rel_deg,motorC_abs_deg,distance_D_mm,force_F_N,yaw_deg,pitch_deg,roll_deg
0,0,0,0,0,0,0,250,0,0.0,0.0,0.0
150,45,45,45,45,0,0,245,0,2.5,0.1,-0.3
300,90,90,90,90,0,0,240,0,5.1,0.2,-0.5
```

**Columns:**
- `time_ms` - Milliseconds since recording started
- `motorX_rel_deg` - Relative position change (resets each session)
- `motorX_abs_deg` - Absolute position (includes previous sessions)
- `distance_X_mm` - Distance sensor reading (if configured)
- `force_X_N` - Force sensor reading (if configured)
- `yaw/pitch/roll_deg` - IMU orientation

---

## Example Workflow (cURL)

```bash
# 1. Detect ports
curl http://127.0.0.1:5000/detect_ports

# 2. Configure
curl -X POST http://127.0.0.1:5000/config \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "com_port": "COM3",
      "motors": {"A": true, "B": true, "C": false},
      "sensors": {"distance": "D"}
    }
  }'

# 3. Connect & Record
curl http://127.0.0.1:5000/connect

# 4. Pull CSV
curl http://127.0.0.1:5000/pull_csv

# 5. Analyze
curl http://127.0.0.1:5000/analyze

# 6. Convert
curl http://127.0.0.1:5000/convert

# 7. Upload
curl http://127.0.0.1:5000/upload_script

# 8. Run
curl http://127.0.0.1:5000/run_script

# 9. Download (returns file)
curl http://127.0.0.1:5000/download -o replay.py
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026 | Frontend integration |
| 1.0 | 2026 | Initial release |