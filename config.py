# ============================================================
# config.py
# ============================================================

from pathlib import Path

# ============================================================
# BASE DIR
# ============================================================

BASE_DIR = Path(__file__).parent

# ============================================================
# SERIAL PORT (will be set from UI)
# ============================================================

SERIAL_PORT = "COM7"  # Default, will be overridden

# ============================================================
# PATHS
# ============================================================

DATA_DIR = BASE_DIR / "backend" / "data"
LOCAL_CSV_PATH = DATA_DIR / "raw_data.csv"
SEGMENTS_PATH = DATA_DIR / "segments.csv"
GENERATED_SCRIPT_PATH = BASE_DIR / "backend" / "data" / "generated_spike.py"
PRODUCE_DATA_SCRIPT = Path("backend/produce_data.py")

# ============================================================
# ROBOT CONFIGURATION (Default - will be overridden by UI)
# ============================================================

ROBOT_CONFIG = {
    "com_port": "COM7",
    "motors": {
        "A": True,
        "B": True,
        "C": True,
    },
    "sensors": {
        "distance": None,
        "force": None,
        "color": None,
    }
}

# ============================================================
# Ensure data directory exists
# ============================================================

DATA_DIR.mkdir(parents=True, exist_ok=True)