# ============================================================
# app.py
# ============================================================

from flask import Flask, jsonify, send_file, render_template, request
from pathlib import Path
import subprocess
import time
import sys
import json
import shutil
import csv as csvmodule
import os

from config import SERIAL_PORT, DATA_DIR, LOCAL_CSV_PATH, SEGMENTS_PATH, GENERATED_SCRIPT_PATH, ROBOT_CONFIG

# ============================================================
# FLASK SETUP
# ============================================================

app = Flask(__name__, 
    template_folder="frontend/templates",
    static_folder="frontend/static"
)

current_config = ROBOT_CONFIG.copy()
COLLECT_DATA_SCRIPT = Path("backend") / "collect_data_2_0.py"

# ============================================================
# PORT DETECTION
# ============================================================

def detect_serial_ports():
    """Detect available serial ports"""
    try:
        import serial.tools.list_ports
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                "port": port.device,
                "description": port.description
            })
        return ports
    except:
        # Fallback: common ports
        common_ports = []
        if sys.platform == "win32":
            common_ports = [f"COM{i}" for i in range(1, 10)]
        else:
            common_ports = [f"/dev/ttyUSB{i}" for i in range(5)]
        return [{"port": p, "description": "Unknown"} for p in common_ports]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def run_mpremote(args, timeout=10):
    """Run mpremote command"""
    try:
        com_port = current_config.get("com_port", SERIAL_PORT)
        cmd = ["mpremote", "connect", com_port] + args
        print(f"DEBUG: Running mpremote: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        print(f"DEBUG: Return code: {result.returncode}, stderr: {result.stderr}")
        return result
    except subprocess.TimeoutExpired:
        print("DEBUG: mpremote timeout")
        return None
    except Exception as e:
        print(f"DEBUG: mpremote error: {e}")
        return None

def upload_collect_data_to_hub():
    """Upload collect_data_2_0.py to hub as main.py"""
    try:
        # Check if file exists
        if not COLLECT_DATA_SCRIPT.exists():
            print(f"DEBUG: File not found at {COLLECT_DATA_SCRIPT.absolute()}")
            return False, f"collect_data_2_0.py not found at {COLLECT_DATA_SCRIPT}"
        
        print(f"DEBUG: Found file at {COLLECT_DATA_SCRIPT.absolute()}")
        
        # Delete old main.py
        print("DEBUG: Deleting old main.py")
        r = run_mpremote(["rm", "/flash/main.py"], timeout=5)
        time.sleep(0.5)
        
        # Upload collect_data_2_0.py as main.py
        print(f"DEBUG: Uploading {COLLECT_DATA_SCRIPT} to hub")
        script_path = str(COLLECT_DATA_SCRIPT.absolute())
        r = run_mpremote(["cp", script_path, ":main.py"], timeout=10)
        
        if r and r.returncode == 0:
            print("DEBUG: Upload successful")
            return True, "Code uploaded"
        else:
            error = r.stderr if r else "Unknown error"
            print(f"DEBUG: Upload failed: {error}")
            return False, f"Upload failed: {error}"
    except Exception as e:
        print(f"DEBUG: Exception in upload_collect_data_to_hub: {e}")
        return False, str(e)

def pull_csv_from_hub():
    """Pull data_log.csv from hub"""
    try:
        lp = str(LOCAL_CSV_PATH.absolute())
        r = run_mpremote(["cp", ":/flash/data_log.csv", lp], timeout=15)
        if r and r.returncode == 0:
            return True
        return False
    except Exception as e:
        return False

def upload_script_to_hub(script_path):
    """Upload script to hub"""
    try:
        if not Path(script_path).exists():
            return False, "Script not found"
        
        r = run_mpremote(["cp", str(Path(script_path).absolute()), ":replay.py"], timeout=10)
        
        if r and r.returncode == 0:
            return True, "Script uploaded"
        else:
            return False, f"Upload failed"
    except Exception as e:
        return False, str(e)

def read_generated_script():
    """Read generated script"""
    try:
        if GENERATED_SCRIPT_PATH.exists():
            return GENERATED_SCRIPT_PATH.read_text()
        return ""
    except Exception as e:
        return f"Error: {e}"

def get_csv_headers():
    """Get headers from CSV"""
    try:
        if not LOCAL_CSV_PATH.exists():
            return []
        with open(LOCAL_CSV_PATH, 'r') as f:
            reader = csvmodule.DictReader(f)
            return reader.fieldnames
    except:
        return []

# ============================================================
# CONFIG ROUTES
# ============================================================

@app.route("/detect_ports")
def detect_ports():
    """Detect available serial ports"""
    try:
        ports = detect_serial_ports()
        return jsonify({"status": "Success", "ports": ports})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e), "ports": []}), 500

@app.route("/config", methods=["GET", "POST"])
def config_route():
    """Get or set robot configuration"""
    global current_config
    
    if request.method == "POST":
        try:
            data = request.get_json()
            new_config = data.get("config")
            
            if not new_config:
                return jsonify({"status": "Error", "message": "Invalid config"}), 400
            
            # Save config to file
            config_path = DATA_DIR / "robot_config.json"
            with open(config_path, "w") as f:
                json.dump(new_config, f, indent=2)
            
            # Upload to hub
            print(f"Uploading config to hub: {config_path}")
            r = run_mpremote(["cp", str(config_path.absolute()), ":/flash/robot_config.json"], timeout=10)
            
            if not r or r.returncode != 0:
                error = r.stderr if r else "Unknown"
                return jsonify({"status": "Error", "message": f"Failed to upload: {error}"}), 500
            
            current_config = new_config
            return jsonify({"status": "Config saved", "config": current_config})
        except Exception as e:
            return jsonify({"status": "Error", "message": str(e)}), 400
    
    return jsonify({"status": "Success", "config": current_config})

# ============================================================
# MAIN ROUTES
# ============================================================

@app.route("/")
def index():
    """Serve UI"""
    return render_template("dashboard.html")

@app.route("/connect")
def connect():
    """Connect and start recording"""
    try:
        print("DEBUG: Starting connect...")
        
        # Upload collect_data_2_0.py as main.py
        success, msg = upload_collect_data_to_hub()
        if not success:
            print(f"DEBUG: Upload failed: {msg}")
            return jsonify({"status": "Error", "message": msg, "output": ""}), 500
        
        time.sleep(1)
        
        print("DEBUG: Executing main.py on hub")
        # Run the script - it will wait for button presses
        r = run_mpremote(["exec", "exec(open('main.py').read())"], timeout=600)
        
        if r and r.returncode == 0:
            print("DEBUG: Execution successful")
            return jsonify({
                "status": "Recording complete",
                "message": "Ready to pull data",
                "output": "✓ Code uploaded\n✓ Recording complete"
            })
        else:
            error = r.stderr if r else "Unknown error"
            print(f"DEBUG: Execution failed: {error}")
            return jsonify({
                "status": "Error",
                "message": "Failed to execute",
                "output": f"✗ Error:\n{error}"
            }), 500
    except Exception as e:
        print(f"DEBUG: Exception in connect: {e}")
        return jsonify({"status": "Error", "message": str(e), "output": ""}), 500

@app.route("/pull_csv")
def pull_csv():
    """Pull CSV from hub"""
    try:
        time.sleep(2)
        
        if pull_csv_from_hub():
            if LOCAL_CSV_PATH.exists():
                size = LOCAL_CSV_PATH.stat().st_size
                headers = get_csv_headers()
                return jsonify({
                    "status": "Success",
                    "csv_size": size,
                    "message": f"Pulled {size} bytes",
                    "output": f"✓ CSV pulled\n✓ Size: {size} bytes\n✓ Headers: {len(headers) if headers else 0} columns",
                    "headers": headers
                })
        
        return jsonify({"status": "Error", "message": "Failed to pull", "output": "✗ Could not find CSV"}), 500
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e), "output": f"✗ Error: {e}"}), 500

@app.route("/analyze")
def analyze():
    """Analyze movement with dynamic config"""
    try:
        if not LOCAL_CSV_PATH.exists():
            return jsonify({"status": "Error", "message": "No CSV", "output": "✗ No CSV file"}), 400
        
        from backend.movement_analysis import run
        output = run(str(LOCAL_CSV_PATH), config=current_config)
        
        # Format output
        result_text = "✓ Analysis complete\n\nDetected Segments:\n"
        for s in output:
            result_text += f"[{s['start']:.0f} - {s['end']:.0f}] {s['type']:20} Speed: {s['avg_speed']:6.2f} deg/s Duration: {s['duration']:.2f}s\n"
        
        return jsonify({
            "status": "Success",
            "message": "Analysis complete",
            "output": result_text
        })
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e), "output": f"✗ Error: {e}"}), 500

@app.route("/get_segments")
def get_segments():
    """Get segments for visualization"""
    try:
        from backend.movement_analysis import run
        segments_list = run(str(LOCAL_CSV_PATH), config=current_config)
        segments = [[s['start'], s['end'], s['type']] for s in segments_list]
        
        return jsonify({"status": "Success", "segments": segments})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@app.route("/convert")
def convert():
    """Generate replay script with dynamic config"""
    try:
        if not LOCAL_CSV_PATH.exists():
            return jsonify({
                "status": "Error",
                "message": "No CSV",
                "output": "✗ No CSV file",
                "script_content": ""
            }), 400
        
        from backend.convert_to_code import generate_spike_script
        
        output_path = DATA_DIR / "replay.py"
        generate_spike_script(str(LOCAL_CSV_PATH), str(output_path), config=current_config)
        
        if output_path.exists():
            shutil.copy(output_path, GENERATED_SCRIPT_PATH)
            
            size = GENERATED_SCRIPT_PATH.stat().st_size
            script_content = read_generated_script()
            return jsonify({
                "status": "Success",
                "script_size": size,
                "message": f"Generated ({size} bytes)",
                "output": f"✓ Script generated\n✓ Size: {size} bytes",
                "script_content": script_content
            })
        else:
            return jsonify({
                "status": "Error",
                "message": "Failed to generate",
                "output": "✗ Script creation failed",
                "script_content": ""
            }), 500
    except Exception as e:
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"✗ Error: {e}",
            "script_content": ""
        }), 500

@app.route("/upload_script")
def upload_script():
    """Upload script to hub"""
    try:
        if not GENERATED_SCRIPT_PATH.exists():
            return jsonify({"status": "Error", "message": "No script", "output": "✗ No script"}), 400
        
        success, msg = upload_script_to_hub(GENERATED_SCRIPT_PATH)
        
        if success:
            return jsonify({
                "status": "Success",
                "message": msg,
                "output": f"✓ {msg}\n✓ Ready to run"
            })
        else:
            return jsonify({
                "status": "Error",
                "message": msg,
                "output": f"✗ {msg}"
            }), 500
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e), "output": f"✗ Error: {e}"}), 500

@app.route("/run_script")
def run_script():
    """Run replay script on hub"""
    try:
        if not GENERATED_SCRIPT_PATH.exists():
            return jsonify({"status": "Error", "message": "No script", "output": "✗ No script"}), 400
        
        r = run_mpremote(["cp", str(GENERATED_SCRIPT_PATH.absolute()), ":replay.py"], timeout=10)
        if r and r.returncode != 0:
            return jsonify({"status": "Error", "message": "Upload failed", "output": "✗ Failed to upload"}), 500
        
        time.sleep(1)
        r = run_mpremote(["exec", "exec(open('replay.py').read())"], timeout=300)
        
        if r and r.returncode == 0:
            output = r.stdout if r.stdout else "Script executed"
            return jsonify({
                "status": "Success",
                "message": "Script completed",
                "output": f"✓ Script ran\n\n{output}"
            })
        else:
            return jsonify({
                "status": "Error",
                "message": "Execution failed",
                "output": f"✗ Error:\n{r.stderr if r else 'Unknown'}"
            }), 500
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e), "output": f"✗ Error: {e}"}), 500

@app.route("/download")
def download():
    """Download script"""
    try:
        if not GENERATED_SCRIPT_PATH.exists():
            return jsonify({"status": "Error", "message": "No script"}), 400
        
        return send_file(
            GENERATED_SCRIPT_PATH,
            as_attachment=True,
            download_name="replay.py"
        )
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG: COLLECT_DATA_SCRIPT path: {COLLECT_DATA_SCRIPT}")
    print(f"DEBUG: COLLECT_DATA_SCRIPT exists: {COLLECT_DATA_SCRIPT.exists()}")
    print(f"DEBUG: Current working directory: {Path.cwd()}")
    app.run(debug=True, host="127.0.0.1", port=5000)