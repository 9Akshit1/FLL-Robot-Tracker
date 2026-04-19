# ============================================================
# config.py
# ============================================================

from pathlib import Path

# ============================================================
# SERIAL PORT
# ============================================================

SERIAL_PORT = "COM7"

# ============================================================
# PATHS
# ============================================================

DATA_DIR = Path("backend/data")
LOCAL_CSV_PATH = DATA_DIR / "raw_data.csv"
SEGMENTS_PATH = DATA_DIR / "segments.csv"
GENERATED_SCRIPT_PATH = DATA_DIR / "generated_spike.py"
PRODUCE_DATA_SCRIPT = Path("backend/produce_data.py")

# ============================================================
# ROBOT CONFIGURATION (Default - will be overridden by UI)
# ============================================================

ROBOT_CONFIG = {
    "motors": {
        "A": {"port": "A", "name": "Left Drive", "type": "motor"},
        "B": {"port": "B", "name": "Right Drive", "type": "motor"},
        "C": {"port": "C", "name": "Attachment", "type": "motor"},
    },
    "sensors": {
        "D": {"port": "D", "name": "Distance", "type": "distance_sensor"},
        "F": {"port": "F", "name": "Force", "type": "force_sensor"},
    },
    "sample_interval_ms": 150,
    "drive_threshold": 12,
    "yaw_threshold": 12,
    "min_segment_ms": 200,
}

# ============================================================
# Ensure data directory exists
# ============================================================

DATA_DIR.mkdir(parents=True, exist_ok=True)