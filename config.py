""""
Title: config.py
Course: ICS4U-02
Author: Akshit Erukulla, Rick He
Summary: 
This config file sets up core paths, default serial port settings, 
and a robot configuration (motors and sensors) for the project, 
while also ensuring the data directory exists. 
It acts as a central place to manage file locations and hardware settings 
that can later be overridden by a user interface.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent

# the serial port will be set from UI
SERIAL_PORT = "COM7"  # Default, will be overridden

# Paths
DATA_DIR = BASE_DIR / "backend" / "data"
LOCAL_CSV_PATH = DATA_DIR / "raw_data.csv"
SEGMENTS_PATH = DATA_DIR / "segments.csv"
GENERATED_SCRIPT_PATH = BASE_DIR / "backend" / "data" / "generated_spike.py"
PRODUCE_DATA_SCRIPT = Path("backend/produce_data.py")

# Robot Configuration (Default - will be overridden by UI)
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

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
