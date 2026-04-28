# app.py - Updated for Local Agent Integration

from flask import Flask, jsonify, send_file, render_template, request
from pathlib import Path
import subprocess
import time
import sys
import json
import shutil
import csv as csvmodule
import os
import requests

from config import SERIAL_PORT, DATA_DIR, LOCAL_CSV_PATH, SEGMENTS_PATH, GENERATED_SCRIPT_PATH, ROBOT_CONFIG

# ============================================================
# FLASK SETUP
# ============================================================

app = Flask(__name__, 
    template_folder="frontend/templates",
    static_folder="frontend/static"
)

current_config = ROBOT_CONFIG.copy()
BASE_DIR = Path(__file__).parent
COLLECT_DATA_SCRIPT = BASE_DIR / "backend" / "collect_data_2_0.py"

# Local Agent Configuration
AGENT_URL = os.getenv("AGENT_URL", "http://localhost:5001")
# Users run local_agent.py on THEIR computer (localhost from their perspective)

# ============================================================
# LOCAL AGENT HELPER
# ============================================================

def call_agent(endpoint, method="GET", data=None, timeout=30):
    """
    Call the local agent running on user's computer
    
    Args:
        endpoint: Agent endpoint (e.g., "/agent/connect")
        method: GET or POST
        data: JSON data to send (for POST)
        timeout: Request timeout in seconds
    
    Returns:
        dict: Response JSON or error dict
    """
    try:
        url = f"{AGENT_URL}{endpoint}"
        print(f"[AGENT] Calling: {method} {url}")
        
        if method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.Timeout:
        print(f"[AGENT] Timeout: {endpoint}")
        return {"error": "Agent timeout - is local_agent.py running?"}
    
    except requests.exceptions.ConnectionError:
        print(f"[AGENT] Connection failed: {AGENT_URL}")
        return {"error": f"Cannot reach agent at {AGENT_URL}. Is local_agent.py running?"}
    
    except Exception as e:
        print(f"[AGENT] Error: {e}")
        return {"error": str(e)}

# ============================================================
# PORT DETECTION (via Local Agent)
# ============================================================

@app.route("/detect_ports")
def detect_ports():
    """
    Detect available serial ports via local agent
    
    The local agent detects ports because it runs on the user's computer
    with USB access. Cloud server just relays the result.
    """
    try:
        print("[PORTS] Requesting port detection from agent...")
        
        result = call_agent("/agent/status")
        
        if "error" in result:
            print(f"[PORTS] Agent error: {result['error']}")
            return jsonify({
                "status": "Error",
                "message": result["error"],
                "ports": []
            }), 500
        
        if result.get("status") == "connected":
            com_port = result.get("com_port", "ROBOT")
            print(f"[PORTS] Robot detected on {com_port}")
            return jsonify({
                "status": "Success",
                "ports": [{
                    "port": com_port,
                    "description": "LEGO Robot (detected by local agent)"
                }]
            })
        else:
            print("[PORTS] Robot not detected")
            return jsonify({
                "status": "Error",
                "message": "Robot not found on USB",
                "ports": []
            }), 400
    
    except Exception as e:
        print(f"[PORTS] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "ports": []
        }), 500

# ============================================================
# CONFIG ROUTES
# ============================================================

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
            
            # Save config locally
            config_path = DATA_DIR / "robot_config.json"
            with open(config_path, "w") as f:
                json.dump(new_config, f, indent=2)
            
            print(f"[CONFIG] Config saved locally")
            
            # Upload to robot via agent
            print("[CONFIG] Uploading to robot via agent...")
            result = call_agent(
                "/agent/config",
                method="POST",
                data={"config": new_config}
            )
            
            if "error" in result:
                print(f"[CONFIG] Agent error: {result['error']}")
                return jsonify({
                    "status": "Error",
                    "message": f"Failed to upload config: {result['error']}"
                }), 500
            
            current_config = new_config
            print("[CONFIG] Config uploaded successfully")
            return jsonify({
                "status": "Config saved",
                "config": current_config
            })
        
        except Exception as e:
            print(f"[CONFIG] Exception: {e}")
            return jsonify({
                "status": "Error",
                "message": str(e)
            }), 400
    
    # GET
    return jsonify({"status": "Success", "config": current_config})

# ============================================================
# MAIN ROUTES (via Local Agent)
# ============================================================

@app.route("/")
def index():
    """Serve UI"""
    return render_template("dashboard.html")

@app.route("/connect")
def connect():
    """
    Get connection script and port for local agent
    """
    try:
        print(f"[CONNECT] Current working directory: {os.getcwd()}")
        print(f"[CONNECT] Looking for script at: {COLLECT_DATA_SCRIPT}")
        print(f"[CONNECT] Absolute path: {COLLECT_DATA_SCRIPT.absolute()}")
        
        # List contents of current directory
        try:
            contents = list(Path(".").iterdir())
            print(f"[CONNECT] Current directory contents: {[str(p) for p in contents]}")
        except Exception as e:
            print(f"[CONNECT] Error listing directory: {e}")
        
        # Check if backend exists
        backend_path = Path("backend")
        if backend_path.exists():
            print(f"[CONNECT] Backend exists, contents: {list(backend_path.iterdir())}")
        else:
            print("[CONNECT] Backend directory not found")
        
        # Get collection script
        if not COLLECT_DATA_SCRIPT.exists():
            print(f"[CONNECT] Script not found: {COLLECT_DATA_SCRIPT}")
            return jsonify({
                "status": "Error",
                "message": "Collection script not found",
                "output": f"✗ {COLLECT_DATA_SCRIPT} not found"
            }), 500
        
        print(f"[CONNECT] Found script at {COLLECT_DATA_SCRIPT}")
        script_content = COLLECT_DATA_SCRIPT.read_text()
        
        # Get the COM port the user selected
        selected_port = current_config.get("com_port", "COM3")
        print(f"[CONNECT] Using port: {selected_port}")
        
        return jsonify({
            "script_content": script_content,
            "com_port": selected_port
        })
    
    except Exception as e:
        print(f"[CONNECT] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"✗ Error: {e}"
        }), 500

@app.route("/pull_csv")
def pull_csv():
    """
    Pull CSV from robot via local agent
    """
    try:
        print("[PULL] Requesting CSV pull from agent...")
        
        # Get the COM port the user selected
        selected_port = current_config.get("com_port", "COM3")
        print(f"[PULL] Using port: {selected_port}")
        
        result = call_agent(
            "/agent/pull",
            method="POST",
            data={"com_port": selected_port}
        )
        
        if "error" in result:
            print(f"[PULL] Agent error: {result['error']}")
            return jsonify({
                "status": "Error",
                "message": result["error"],
                "output": f"✗ Error: {result['error']}"
            }), 500
        
        # Save CSV locally for analysis
        csv_content = result.get("csv_content", "")
        if not csv_content:
            print("[PULL] Empty CSV received")
            return jsonify({
                "status": "Error",
                "message": "Empty CSV",
                "output": "✗ CSV is empty"
            }), 500
        
        LOCAL_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_CSV_PATH.write_text(csv_content)
        csv_size = result.get("csv_size", len(csv_content))
        
        # Get headers
        headers = csv_content.split('\n')[0].split(',') if csv_content else []
        
        print(f"[PULL] CSV received ({csv_size} bytes)")
        return jsonify({
            "status": "Success",
            "csv_size": csv_size,
            "message": "Pulled from robot",
            "output": f"✓ CSV pulled\n✓ Size: {csv_size} bytes\n✓ Headers: {len(headers)} columns",
            "headers": headers
        })
    
    except Exception as e:
        print(f"[PULL] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"✗ Error: {e}"
        }), 500

@app.route("/analyze")
def analyze():
    """Analyze movement with dynamic config"""
    try:
        print("[ANALYZE] Starting analysis...")
        
        if not LOCAL_CSV_PATH.exists():
            print("[ANALYZE] CSV file not found")
            return jsonify({
                "status": "Error",
                "message": "No CSV",
                "output": "✗ No CSV file. Pull data first."
            }), 400
        
        from backend.movement_analysis import run
        output = run(str(LOCAL_CSV_PATH), config=current_config)
        
        # Format output
        result_text = "✓ Analysis complete\n\nDetected Segments:\n"
        for s in output:
            result_text += f"[{s['start']:.0f} - {s['end']:.0f}] {s['type']:20} Speed: {s['avg_speed']:6.2f} deg/s Duration: {s['duration']:.2f}s\n"
        
        print(f"[ANALYZE] Analysis complete - {len(output)} segments detected")
        return jsonify({
            "status": "Success",
            "message": "Analysis complete",
            "output": result_text
        })
    
    except Exception as e:
        print(f"[ANALYZE] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"✗ Error: {e}"
        }), 500

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
        print("[CONVERT] Starting code generation...")
        
        if not LOCAL_CSV_PATH.exists():
            print("[CONVERT] CSV not found")
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
            script_content = GENERATED_SCRIPT_PATH.read_text()
            print(f"[CONVERT] Script generated ({size} bytes)")
            return jsonify({
                "status": "Success",
                "script_size": size,
                "message": f"Generated ({size} bytes)",
                "output": f"✓ Script generated\n✓ Size: {size} bytes",
                "script_content": script_content
            })
        else:
            print("[CONVERT] Script creation failed")
            return jsonify({
                "status": "Error",
                "message": "Failed to generate",
                "output": "✗ Script creation failed",
                "script_content": ""
            }), 500
    except Exception as e:
        print(f"[CONVERT] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"✗ Error: {e}",
            "script_content": ""
        }), 500

@app.route("/upload_script")
def upload_script():
    """
    Upload script to robot via local agent
    """
    try:
        print("[UPLOAD] Starting script upload via agent...")
        
        if not GENERATED_SCRIPT_PATH.exists():
            print("[UPLOAD] Script not found")
            return jsonify({
                "status": "Error",
                "message": "No script",
                "output": "✗ No script generated yet"
            }), 400
        
        # Get the COM port the user selected
        selected_port = current_config.get("com_port", "COM3")
        print(f"[UPLOAD] Using port: {selected_port}")
        
        script_content = GENERATED_SCRIPT_PATH.read_text()
        
        result = call_agent(
            "/agent/upload",
            method="POST",
            data={
                "script_content": script_content,
                "com_port": selected_port
            }
        )
        
        if "error" in result:
            print(f"[UPLOAD] Agent error: {result['error']}")
            return jsonify({
                "status": "Error",
                "message": result["error"],
                "output": f"✗ {result['error']}"
            }), 500
        
        print("[UPLOAD] Script uploaded successfully")
        return jsonify({
            "status": "Success",
            "message": "Script uploaded",
            "output": "✓ Script uploaded to robot\n✓ Ready to run"
        })
    
    except Exception as e:
        print(f"[UPLOAD] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"✗ Error: {e}"
        }), 500

@app.route("/run_script")
def run_script():
    """
    Execute replay script on robot via local agent
    """
    try:
        print("[RUN] Starting script execution via agent...")
        
        if not GENERATED_SCRIPT_PATH.exists():
            print("[RUN] Script not found")
            return jsonify({
                "status": "Error",
                "message": "No script",
                "output": "✗ No script to run"
            }), 400
        
        # Get the COM port the user selected
        selected_port = current_config.get("com_port", "COM3")
        print(f"[RUN] Using port: {selected_port}")
        
        result = call_agent(
            "/agent/run",
            method="POST",
            data={"com_port": selected_port},
            timeout=600  # 10 minutes
        )
        
        if "error" in result:
            print(f"[RUN] Agent error: {result['error']}")
            return jsonify({
                "status": "Error",
                "message": result["error"],
                "output": f"✗ {result['error']}"
            }), 500
        
        output = result.get("output", "Script executed")
        print("[RUN] Script execution completed")
        return jsonify({
            "status": "Success",
            "message": "Script executed",
            "output": f"✓ Script ran\n\n{output}"
        })
    
    except Exception as e:
        print(f"[RUN] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"✗ Error: {e}"
        }), 500

@app.route("/download")
def download():
    """Download script"""
    try:
        if not GENERATED_SCRIPT_PATH.exists():
            return jsonify({"status": "Error", "message": "No script"}), 400
        
        print("[DOWNLOAD] Serving script download...")
        return send_file(
            GENERATED_SCRIPT_PATH,
            as_attachment=True,
            download_name="replay.py"
        )
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

# ============================================================
# AGENT STATUS ENDPOINT
# ============================================================

@app.route("/agent_status")
def agent_status():
    """Check if local agent is reachable"""
    result = call_agent("/agent/status")
    
    if "error" in result:
        print(f"[STATUS] Agent unreachable: {result['error']}")
        return jsonify({
            "agent": "disconnected",
            "error": result["error"],
            "agent_url": AGENT_URL
        }), 500
    else:
        print("[STATUS] Agent connected")
        return jsonify({
            "agent": "connected",
            "com_port": result.get("com_port"),
            "agent_url": AGENT_URL
        })

@app.route("/debug_files")
def debug_files():
    """Debug endpoint to list files"""
    try:
        base_dir = Path(__file__).parent
        files = []
        for item in base_dir.iterdir():
            files.append(str(item))
        return jsonify({"base_dir": str(base_dir), "files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Starting FLL Robot Tracker")
    print(f"Local Agent URL: {AGENT_URL}")
    print(f"Data Directory: {DATA_DIR}")
    app.run(debug=True, host="127.0.0.1", port=5000)