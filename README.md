# FLL Robot Tracker

A web-based system for LEGO First Robotics League teams to record, analyze, and replay robot movement.

## What It Does

1. **Record** - Connect to your robot and capture motor/sensor data while it moves
2. **Analyze** - Automatically detect movement patterns (driving straight, turning, stationary)
3. **Generate** - Convert recorded movements into a Python replay script
4. **Replay** - Execute the generated script on your robot to repeat the exact motion

## Quick Start

### Requirements
- Python 3.8+
- A LEGO SPIKE Prime hub with motors connected
- `mpremote` installed (`pip install mpremote`)
- Serial port access (USB cable to robot)

### Installation

```bash
# 1. Clone/download this project
cd FLL-Robot-Tracker

# 2. Setup Virtual Environment
python -m env venv
venv/Scripts/activate

# 3. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Visit `http://127.0.0.1:5000` in your browser.

### First Time Setup

1. **Connect Robot**
   - Plug in your LEGO SPIKE Prime via USB
   - Click "Detect Ports" to find the serial port

2. **Configure**
   - Select which ports have motors/sensors
   - Click "Save & Upload Config"

3. **Record Motion**
   - Click "Connect & Record"
   - Press LEFT button on robot to start, RIGHT to stop
   - Motion data saves to robot's storage

4. **Analyze & Replay**
   - Click "Pull Data" to download CSV from robot
   - Click "Analyze" to detect movement patterns
   - Click "Generate" to create Python script
   - Click "Upload" then "Run" to replay on robot


## How It Works (Technical)

### Data Flow
```
Robot (records data)
  ↓ [USB via mpremote]
Server (analyzes)
  ↓
CSV file with motor positions & timestamps
  ↓ [movement_analysis.py]
Detected segments (drive, turn, stop)
  ↓ [convert_to_code.py]
Python script with motor commands
  ↓ [mpremote + USB]
Robot (replays)
```

## Testing

Run unit tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=backend --cov-report=html
```

## Deployment

### Local Network
```bash
python app.py
# Accessible at http://192.168.1.x:5000 (replace x with your IP)
```

## License

MIT License - Use freely for educational purposes.

---

**Last Updated:** 2026
**Version:** 2.1