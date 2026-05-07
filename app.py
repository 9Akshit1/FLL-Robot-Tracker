# app.py - FINAL FIXED VERSION
# - analyze route accepts BOTH GET and POST
# - Better error handling for all steps

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
import traceback

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

# ============================================================
# LOCAL AGENT HELPER
# ============================================================

def call_agent(endpoint, method="GET", data=None, timeout=30):
    """Call the local agent running on user's computer"""
    try:
        url = f"{AGENT_URL}{endpoint}"
        print(f"[AGENT] Calling: {method} {url} (timeout: {timeout}s)")

        if method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)

        print(f"[AGENT] Response status: {response.status_code}")
        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout as e:
        print(f"[AGENT] TIMEOUT: {endpoint} (waited {timeout}s)")
        traceback.print_exc()
        return {"error": f"Agent timeout after {timeout}s - is local_agent.py running?"}

    except requests.exceptions.ConnectionError as e:
        print(f"[AGENT] CONNECTION FAILED: {AGENT_URL}")
        print(f"[AGENT] Error details: {e}")
        traceback.print_exc()
        return {"error": f"Cannot reach agent at {AGENT_URL}. Is local_agent.py running?"}

    except Exception as e:
        print(f"[AGENT] EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {"error": str(e)}

# ============================================================
# PORT DETECTION (via Local Agent)
# ============================================================

@app.route("/detect_ports")
def detect_ports():
    """Detect available serial ports via local agent"""
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
    """Get connection script and port for local agent"""
    try:
        print(f"[CONNECT] Current working directory: {os.getcwd()}")
        print(f"[CONNECT] Looking for script at: {COLLECT_DATA_SCRIPT}")

        if not COLLECT_DATA_SCRIPT.exists():
            print(f"[CONNECT] Script not found: {COLLECT_DATA_SCRIPT}")
            return jsonify({
                "status": "Error",
                "message": "Collection script not found",
                "output": f"Error: {COLLECT_DATA_SCRIPT} not found"
            }), 500

        print(f"[CONNECT] Found script at {COLLECT_DATA_SCRIPT}")
        script_content = COLLECT_DATA_SCRIPT.read_text()

        selected_port = current_config.get("com_port")

        if not selected_port:
            return jsonify({
                "status": "Error",
                "message": "No COM port selected. Please select a port from the available ports first.",
                "output": "Error: Please select a COM port"
            }), 400

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
            "output": f"Error: {e}"
        }), 500

@app.route("/save_csv", methods=["POST"])
def save_csv():
    """Save CSV content pulled from agent"""
    try:
        data = request.get_json()
        csv_content = data.get("csv_content", "")

        LOCAL_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(LOCAL_CSV_PATH, "w", encoding="utf-8") as f:
            f.write(csv_content)

        size = LOCAL_CSV_PATH.stat().st_size
        print(f"[CSV] Saved CSV ({size} bytes)")

        return jsonify({
            "status": "Success",
            "message": "CSV saved",
            "output": f"OK: CSV saved ({size} bytes)"
        })

    except Exception as e:
        print(f"[CSV] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"Error: {e}"
        }), 500

@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    """Run movement analysis on recorded CSV - ACCEPTS BOTH GET AND POST"""
    try:
        if not LOCAL_CSV_PATH.exists():
            print("[ANALYZE] No CSV file")
            return jsonify({
                "status": "Error",
                "message": "No CSV file",
                "output": "Error: No CSV data. Please pull data first."
            }), 400

        print(f"[ANALYZE] Analyzing {LOCAL_CSV_PATH}")
        print(f"[ANALYZE] CSV file size: {LOCAL_CSV_PATH.stat().st_size} bytes")
        
        # CRITICAL: Try/except for each major step
        try:
            print("[ANALYZE] Step 1: Importing movement_analysis...")
            from backend import movement_analysis
            print("[ANALYZE] Step 1 OK: Import successful")
            
        except ImportError as e:
            print(f"[ANALYZE] IMPORT FAILED: {e}")
            traceback.print_exc()
            return jsonify({
                "status": "Error",
                "message": f"Cannot import movement_analysis: {e}",
                "output": f"Error: Cannot import module: {e}"
            }), 500
        
        try:
            print("[ANALYZE] Step 2: Running movement_analysis.run()...")
            success = movement_analysis.run(str(LOCAL_CSV_PATH), str(SEGMENTS_PATH))
            print(f"[ANALYZE] Step 2 OK: Analysis returned {success}")
            
            if not success:
                print("[ANALYZE] Analysis returned False")
                return jsonify({
                    "status": "Error",
                    "message": "Analysis failed",
                    "output": "Error: Movement analysis returned False"
                }), 500
            
        except Exception as e:
            print(f"[ANALYZE] ANALYSIS FAILED: {e}")
            traceback.print_exc()
            return jsonify({
                "status": "Error",
                "message": f"Analysis execution failed: {e}",
                "output": f"Error during analysis: {e}"
            }), 500
        
        try:
            print("[ANALYZE] Step 3: Reading segments.json...")
            with open(SEGMENTS_PATH, 'r') as f:
                segments = json.load(f)
            print(f"[ANALYZE] Step 3 OK: Loaded {len(segments)} segments")
            
        except FileNotFoundError:
            print(f"[ANALYZE] segments.json not found at {SEGMENTS_PATH}")
            traceback.print_exc()
            return jsonify({
                "status": "Error",
                "message": f"segments.json not created",
                "output": f"Error: {SEGMENTS_PATH} not found"
            }), 500
        
        except json.JSONDecodeError as e:
            print(f"[ANALYZE] segments.json is not valid JSON: {e}")
            traceback.print_exc()
            return jsonify({
                "status": "Error",
                "message": f"segments.json is invalid: {e}",
                "output": f"Error: Invalid JSON in segments.json"
            }), 500
        
        except Exception as e:
            print(f"[ANALYZE] Failed to read segments: {e}")
            traceback.print_exc()
            return jsonify({
                "status": "Error",
                "message": f"Failed to read segments: {e}",
                "output": f"Error: {e}"
            }), 500
        
        # Build output text
        output_text = f"Analysis Complete\n"
        
        # Calculate total time from segments
        if segments:
            total_time_ms = max(seg.get('end_ms', 0) for seg in segments)
            output_text += f"Total time: {total_time_ms:.0f}ms\n"
        
        output_text += f"Found {len(segments)} movement segments\n\n"

        for i, seg in enumerate(segments, 1):
            start = seg.get('start_ms', 0)
            end = seg.get('end_ms', 0)
            duration = seg.get('duration_ms', 0)
            desc = seg.get('description', 'Unknown')

            output_text += f"[{i}] {desc}: {start:.0f}ms - {end:.0f}ms ({duration:.0f}ms)\n"

        print("[ANALYZE] Analysis complete - returning success")
        return jsonify({
            "status": "Success",
            "message": "Analysis complete",
            "segments": segments,
            "summary": {},
            "output": output_text
        })

    except Exception as e:
        print(f"[ANALYZE] OUTER EXCEPTION: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"Error: {e}"
        }), 500

@app.route("/convert")
def convert():
    """Convert analyzed data to replay script"""
    try:
        print("[CONVERT] Starting conversion...")

        if not LOCAL_CSV_PATH.exists():
            print("[CONVERT] CSV file not found")
            return jsonify({
                "status": "Error",
                "message": "No CSV data",
                "output": "Error: No CSV data found. Please run Analyze first."
            }), 400

        # Import and run conversion
        try:
            from backend import convert_to_code
            
            print("[CONVERT] Running convert_to_code.generate_spike_script()...")
            
            # Define paths for timeline (upload) and display (UI preview) scripts
            timeline_script_path = GENERATED_SCRIPT_PATH  # This gets uploaded to robot
            display_script_path = GENERATED_SCRIPT_PATH.parent / "generated_spike_display.py"  # For UI
            
            # Call conversion function - returns both scripts
            timeline_script, display_script = convert_to_code.generate_spike_script(
                str(LOCAL_CSV_PATH), 
                str(timeline_script_path),
                str(display_script_path),
                config=current_config
            )

            if GENERATED_SCRIPT_PATH.exists():
                timeline_size = GENERATED_SCRIPT_PATH.stat().st_size
                display_size = len(display_script) if display_script else 0
                print(f"[CONVERT] Timeline script generated ({timeline_size} bytes)")
                print(f"[CONVERT] Display script generated ({display_size} bytes)")

                return jsonify({
                    "status": "Success",
                    "timeline_size": timeline_size,
                    "display_size": display_size,
                    "message": f"Generated (Timeline: {timeline_size} bytes, Display: {display_size} bytes)",
                    "output": f"OK: Script generated\nOK: Timeline size: {timeline_size} bytes\nOK: Ready to upload",
                    "script_content": display_script  # SHOW DISPLAY VERSION IN UI
                })
            else:
                print("[CONVERT] Timeline script creation failed - file doesn't exist")
                return jsonify({
                    "status": "Error",
                    "message": "Failed to generate script",
                    "output": "Error: Script file was not created",
                    "script_content": ""
                }), 500
                
        except ImportError as e:
            print(f"[CONVERT] Import error: {e}")
            traceback.print_exc()
            return jsonify({
                "status": "Error",
                "message": f"Cannot import convert_to_code: {e}",
                "output": f"Error: {e}"
            }), 500
        except Exception as e:
            print(f"[CONVERT] Error running conversion: {e}")
            traceback.print_exc()
            return jsonify({
                "status": "Error",
                "message": str(e),
                "output": f"Error: {e}"
            }), 500

    except Exception as e:
        print(f"[CONVERT] Exception: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"Error: {e}"
        }), 500

@app.route("/upload", methods=["POST", "GET"])
def upload():
    """Upload script to robot via local agent"""
    try:
        print("[UPLOAD] Starting script upload via agent...")

        if not GENERATED_SCRIPT_PATH.exists():
            print("[UPLOAD] Script not found")
            return jsonify({
                "status": "Error",
                "message": "No script",
                "output": "Error: No script generated yet"
            }), 400

        selected_port = current_config.get("com_port")

        if not selected_port:
            return jsonify({
                "status": "Error",
                "message": "No COM port selected. Please select a port from the available ports first."
            }), 400

        print(f"[UPLOAD] Using port: {selected_port}")

        script_content = GENERATED_SCRIPT_PATH.read_text()

        result = call_agent(
            "/agent/upload",
            method="POST",
            data={
                "script": script_content,
                "com_port": selected_port
            }
        )

        if "error" in result:
            print(f"[UPLOAD] Agent error: {result['error']}")
            return jsonify({
                "status": "Error",
                "message": result["error"],
                "output": f"Error: {result['error']}"
            }), 500

        print("[UPLOAD] Script uploaded successfully")
        return jsonify({
            "status": "Success",
            "message": "Script uploaded",
            "output": "OK: Script uploaded to robot\nOK: Ready to run"
        })

    except Exception as e:
        print(f"[UPLOAD] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": f"Error: {e}"
        }), 500

@app.route("/run_script", methods=["POST", "GET"])
def run_script():
    """Execute replay script on robot via local agent"""
    try:
        print("[RUN] Starting script execution via agent...")

        if not GENERATED_SCRIPT_PATH.exists():
            print("[RUN] Script not found")
            return jsonify({
                "status": "Error",
                "message": "No script",
                "output": "Error: No script to run"
            }), 400

        selected_port = current_config.get("com_port")

        if not selected_port:
            return jsonify({
                "status": "Error",
                "message": "No COM port selected"
            }), 400

        print(f"[RUN] Using port: {selected_port}")

        result = call_agent(
            "/agent/run",
            method="POST",
            data={"com_port": selected_port},
            timeout=120
        )

        if "error" in result:
            print(f"[RUN] Agent error: {result['error']}")
            return jsonify({
                "status": "Error",
                "message": result["error"],
                "output": "Error: " + result["error"]
            }), 500

        output = result.get("output", "Script executed")
        print("[RUN] Script execution completed")

        return jsonify({
            "status": "Success",
            "message": "Script executed",
            "output": f"Script ran successfully\n\n{output}"
        })

    except Exception as e:
        print(f"[RUN] Exception: {e}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "output": "Error: " + str(e)
        }), 500

@app.route("/download")
def download():
    """Download the DISPLAY script"""
    try:
        display_script_path = GENERATED_SCRIPT_PATH.parent / "generated_spike_display.py"
        
        if display_script_path.exists():
            print("[DOWNLOAD] Serving DISPLAY script...")
            return send_file(
                display_script_path,
                as_attachment=True,
                download_name="replay_semantic.py"
            )
        
        if GENERATED_SCRIPT_PATH.exists():
            print("[DOWNLOAD] Display script not found, serving TIMELINE script...")
            return send_file(
                GENERATED_SCRIPT_PATH,
                as_attachment=True,
                download_name="replay_timeline.py"
            )
        
        return jsonify({"status": "Error", "message": "No script generated"}), 400

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

@app.route("/get_generated_script")
def get_generated_script():
    """Get the generated replay script"""
    try:
        if not GENERATED_SCRIPT_PATH.exists():
            return jsonify({"error": "Script not generated"}), 404

        script = GENERATED_SCRIPT_PATH.read_text()
        return jsonify({"script": script})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug_csv_full")
def debug_csv_full():
    """Full debug of CSV file"""
    try:
        if not LOCAL_CSV_PATH.exists():
            return jsonify({"error": "CSV file does not exist", "path": str(LOCAL_CSV_PATH)})

        content = LOCAL_CSV_PATH.read_text()
        lines = content.split('\n')

        motor_data = []
        if len(lines) > 1:
            for i, line in enumerate(lines[1:11]):
                if line:
                    motor_data.append(line.split(',')[0:4])

        return jsonify({
            "path": str(LOCAL_CSV_PATH),
            "file_size": LOCAL_CSV_PATH.stat().st_size,
            "total_lines": len(lines),
            "header": lines[0] if lines else "NO HEADER",
            "first_10_rows": motor_data,
            "full_content_length": len(content)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    print(f"[ERROR] Internal server error: {error}")
    traceback.print_exc()
    return jsonify({"error": "Internal server error"}), 500

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Starting FLL Robot Tracker")
    print(f"Local Agent URL: {AGENT_URL}")
    print(f"Data Directory: {DATA_DIR}")
    app.run(debug=True, host="127.0.0.1", port=5000)