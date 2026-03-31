import os
import subprocess
import time
from flask import Flask, render_template, jsonify, send_file
from pathlib import Path
from backend.movement_analysis import run as analyze_movements
from backend.convert_to_code import generate_spike_script

# ---------------- CONFIG ----------------
SERIAL_PORT = "COM5"  # hub COM port
DATA_DIR = Path("backend/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOCAL_CSV_PATH = DATA_DIR / "raw_data.csv"
PRODUCE_DATA_SCRIPT = "backend/produce_data.py"
GENERATED_PATH = DATA_DIR / "generated_spike.py"
HUB_CSV_PATH = "flash/data_log.csv"

# ---------------- FLASK ----------------
app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

# Helper functions
def send_command_to_hub(command: str) -> bool:
    """
    Send a command to the hub via exec
    This sets global variables in the running program
    """
    try:
        subprocess.run(
            ["mpremote", "connect", SERIAL_PORT, "exec", command],
            check=True,
            timeout=5
        )
        return True
    except Exception as e:
        print(f"Error sending command: {e}")
        return False

def pull_file_from_hub(remote_path: str, local_path) -> bool:
    """Download a file from the hub"""
    try:
        # Convert Path objects to POSIX paths (forward slashes)
        if hasattr(local_path, 'as_posix'):
            local_path = local_path.as_posix()
        else:
            local_path = str(local_path).replace('\\', '/')
        
        subprocess.run(
            ["mpremote", "connect", SERIAL_PORT, "cp", f":{remote_path}", local_path],
            check=True,
            timeout=10
        )
        return True
    except Exception as e:
        print(f"Error pulling file: {e}")
        return False

def list_hub_files() -> str:
    """List files in /flash/ directory on hub"""
    try:
        result = subprocess.run(
            ["mpremote", "connect", SERIAL_PORT, "fs", "ls", "/flash/"],
            capture_output=True,
            timeout=5,
            text=True
        )
        return result.stdout if result.returncode == 0 else "Directory empty or inaccessible"
    except Exception as e:
        return f"Error: {e}"

def hub_file_size(remote_path: str) -> int:
    """Get file size on hub. Returns -1 if not found"""
    try:
        result = subprocess.run(
            ["mpremote", "connect", SERIAL_PORT, "fs", "ls", f"/flash/{remote_path}"],
            capture_output=True,
            timeout=5,
            text=True
        )
        if result.returncode == 0:
            # Parse: "         528 data_log.csv"
            parts = result.stdout.strip().split()
            if parts:
                return int(parts[0])
        return -1
    except Exception:
        return -1

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/connect")
def connect():
    """Uploads produce_data.py to hub as main.py"""
    try:
        subprocess.run(
            ["mpremote", "connect", SERIAL_PORT, "cp", PRODUCE_DATA_SCRIPT, ":main.py"],
            check=True,
            timeout=10
        )
        # Give hub time to restart and run main.py
        time.sleep(3)
        return jsonify({"status": "Connected and code uploaded. Hub is ready."})
    except Exception as e:
        return jsonify({"status": f"Failed to connect/upload: {e}"})

@app.route("/start_recording")
def start_recording():
    """Set start_flag = True on hub to start recording"""
    try:
        # Execute Python on the hub to set the global variable
        if send_command_to_hub("start_flag = True"):
            time.sleep(0.5)
            return jsonify({"status": "Recording started on hub"})
        else:
            return jsonify({"status": "Failed to send START command"})
    except Exception as e:
        return jsonify({"status": f"Failed to start recording: {e}"})

@app.route("/stop_recording")
def stop_recording():
    """Set stop_flag = True on hub to stop recording and pull CSV"""
    try:
        # 1. Send STOP command via exec
        if not send_command_to_hub("stop_flag = True"):
            return jsonify({"status": "Failed to send STOP command"})
        
        # 2. Wait for hub to process and close file
        time.sleep(2)
        
        # 3. Check file size to ensure data was written
        csv_size = hub_file_size("data_log.csv")
        if csv_size <= 0:
            hub_files = list_hub_files()
            return jsonify({
                "status": f"No data recorded. File size: {csv_size}. Hub contents:\n{hub_files}"
            })
        
        # 4. Pull CSV from hub
        if pull_file_from_hub(HUB_CSV_PATH, LOCAL_CSV_PATH):
            return jsonify({
                "status": f"Recording stopped and data pulled ({csv_size} bytes)"
            })
        else:
            return jsonify({"status": "Failed to pull CSV from hub"})
            
    except Exception as e:
        return jsonify({"status": f"Failed to stop/pull data: {e}"})

@app.route("/convert")
def convert():
    """Run movement analysis and generate new Spike code"""
    try:
        # Check if CSV file exists locally
        if not LOCAL_CSV_PATH.exists():
            return jsonify({"status": f"Error: CSV file not found at {LOCAL_CSV_PATH}. Did you record data?"})
        
        # Check if file has content
        file_size = LOCAL_CSV_PATH.stat().st_size
        if file_size < 50:  # Just header would be ~200 bytes, so < 50 means something wrong
            return jsonify({"status": f"CSV file too small ({file_size} bytes). Did the recording work?"})
        
        analyze_movements(str(LOCAL_CSV_PATH))
        generate_spike_script(str(LOCAL_CSV_PATH), str(GENERATED_PATH))
        return jsonify({"status": "Conversion complete"})
    except FileNotFoundError as e:
        return jsonify({"status": f"File not found: {e}"})
    except Exception as e:
        return jsonify({"status": f"Conversion failed: {e}"})

@app.route("/download")
def download():
    """Allow user to download the generated Spike Python file"""
    try:
        return send_file(GENERATED_PATH, as_attachment=True)
    except Exception as e:
        return jsonify({"status": f"Download failed: {e}"})

@app.route("/debug")
def debug():
    """Debug endpoint to check hub and local status"""
    hub_files = list_hub_files()
    csv_local_exists = LOCAL_CSV_PATH.exists()
    csv_local_size = LOCAL_CSV_PATH.stat().st_size if csv_local_exists else 0
    csv_hub_size = hub_file_size("data_log.csv")
    
    return jsonify({
        "hub_files": hub_files,
        "local_csv_exists": csv_local_exists,
        "local_csv_size": csv_local_size,
        "hub_csv_size": csv_hub_size,
        "local_csv_path": str(LOCAL_CSV_PATH),
        "generated_code_exists": GENERATED_PATH.exists(),
        "generated_code_size": GENERATED_PATH.stat().st_size if GENERATED_PATH.exists() else 0
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)