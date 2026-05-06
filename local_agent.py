#!/usr/bin/env python3
"""
FLL Robot Tracker - Local Agent
Ready for PyInstaller compilation to EXE

Changes from original:
- Removed bootstrap/venv logic (not needed in EXE)
- Changed all mpremote calls to use sys.executable -m mpremote
- Cleaned up path detection (not needed in EXE)
"""

import os
import sys
import subprocess
import json
import time
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

COM_PORT = os.getenv("COM_PORT", "COM3")

AGENT_DATA_DIR = Path("./agent_data")
AGENT_DATA_DIR.mkdir(exist_ok=True)

LOG_DIR = AGENT_DATA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"agent_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

# ============================================================
# CORS SUPPORT
# ============================================================

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/agent/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({'status': 'ok'})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response, 200

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
    except Exception as e:
        logger.warning(f"Could not detect ports: {e}")
        if os.name == 'nt':
            return [{"port": f"COM{i}", "description": "Potential Serial Port"} for i in range(1, 10)]
        else:
            return [{"port": f"/dev/ttyUSB{i}", "description": "Potential Serial Port"} for i in range(5)]

# ============================================================
# ENDPOINTS
# ============================================================

@app.route("/agent/detect_ports")
def detect_ports():
    """Detect available serial ports"""
    logger.info("Port detection requested")
    
    try:
        ports = detect_serial_ports()
        
        if ports:
            logger.info(f"Found {len(ports)} port(s)")
            return jsonify({
                "status": "success",
                "ports": ports,
                "message": f"Found {len(ports)} port(s)"
            })
        else:
            logger.info("No ports found")
            return jsonify({
                "status": "success",
                "ports": [],
                "message": "No ports found. Connect a device via USB."
            })
    
    except Exception as e:
        logger.error(f"Port detection failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "ports": []
        }), 500

@app.route("/agent/ping")
def ping():
    """Simple ping to check agent is running"""
    logger.debug("Ping received")
    return jsonify({
        "status": "ok",
        "message": "Agent is running"
    })

@app.route("/agent/info")
def agent_info():
    """Get agent information"""
    return jsonify({
        "agent": "FLL Robot Tracker - Local Agent",
        "version": "2.0",
        "data_dir": str(AGENT_DATA_DIR),
        "status": "running"
    })

# ============================================================
# CONNECTION ENDPOINT
# ============================================================

@app.route("/agent/connect", methods=["POST"])
def agent_connect():
    """Upload and execute data collection script"""
    try:
        logger.info("Connect request received")
        
        data = request.get_json()
        script_content = data.get("script_content") or data.get("script")
        selected_port = data.get("com_port", COM_PORT)
        
        if not script_content:
            logger.error("Script content not provided")
            return jsonify({"error": "script_content required"}), 400
        
        logger.info(f"Received collection script ({len(script_content)} bytes)")
        
        # FIXED: UTF-8 encoding
        script_path = AGENT_DATA_DIR / "collect.py"
        script_path.write_text(script_content, encoding='utf-8')
        logger.info(f"Saved collection script to {script_path}")
        
        # Upload to robot
        logger.info(f"Uploading to {selected_port}...")
        cmd = [sys.executable, "-m", "mpremote", "connect", selected_port, "cp", str(script_path.absolute()), ":main.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            error = result.stderr if result else "Unknown error"
            logger.error(f"Upload failed: {error}")
            return jsonify({"error": f"Upload failed: {error[:100]}"}), 500
        
        logger.info("Script uploaded successfully")
        time.sleep(1)
        
        # Execute on robot
        logger.info(f"Executing on {selected_port}...")
        cmd = [sys.executable, "-m", "mpremote", "connect", selected_port, "exec", "exec(open('main.py').read())"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error"
            logger.error(f"Execution failed: {error_msg}")
            return jsonify({
                "status": "warning",
                "message": "Script uploaded but execution may have failed",
                "error": error_msg[:200],
                "path": str(script_path)
            }), 200
        
        logger.info("Collection script executed successfully")
        
        return jsonify({
            "status": "success",
            "message": "Collection script uploaded and executed",
            "path": str(script_path)
        }), 200
    
    except Exception as e:
        logger.error(f"Connect failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/agent/pull", methods=["GET", "POST"])
def agent_pull():
    """Pull CSV data from robot"""
    logger.info("Pull CSV request received")
    
    try:
        data = request.get_json(silent=True) or {}
        selected_port = data.get("com_port", COM_PORT)
        
        csv_path = AGENT_DATA_DIR / "data_log.csv"
        
        logger.info(f"Pulling CSV from {selected_port}...")
        cmd = [sys.executable, "-m", "mpremote", "connect", selected_port, "cp", ":data_log.csv", str(csv_path.absolute())]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            error = result.stderr if result else "CSV not found on robot"
            logger.error(f"Pull failed: {error}")
            return jsonify({"error": f"Pull failed: {error[:100]}"}), 500
        
        if not csv_path.exists():
            logger.error("CSV file not found after pull")
            return jsonify({"error": "CSV file not created"}), 500
        
        # FIXED: UTF-8 encoding
        csv_content = csv_path.read_text(encoding='utf-8', errors='ignore')
        csv_size = csv_path.stat().st_size
        
        logger.info(f"CSV pulled ({csv_size} bytes)")
        return jsonify({
            "status": "success",
            "csv_size": csv_size,
            "csv_content": csv_content,
            "message": "CSV pulled successfully"
        })
    
    except Exception as e:
        logger.error(f"Pull failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/agent/config", methods=["POST"])
def agent_config():
    """Upload robot configuration"""
    logger.info("Config upload request received")
    
    try:
        data = request.get_json()
        if not data or not data.get("config"):
            return jsonify({"error": "config data required"}), 400
        
        config_data = data["config"]
        
        # FIXED: UTF-8 encoding
        config_path = AGENT_DATA_DIR / "robot_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
            
        logger.info(f"Config saved locally to {config_path}")
        
        return jsonify({
            "status": "success",
            "message": "Configuration saved to local agent"
        })
    
    except Exception as e:
        logger.error(f"Config upload failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/agent/upload", methods=["POST"])
def agent_upload():
    """Upload replay script"""
    logger.info("Upload script request received")
    
    try:
        data = request.get_json()
        script_content = data.get("script") or data.get("script_content")
        
        if not data or not script_content:
            logger.error("Script content not provided")
            return jsonify({"error": "script required"}), 400
        
        selected_port = data.get("com_port", COM_PORT)
        auto_run = data.get("auto_run", False)
        
        # FIXED: UTF-8 encoding
        script_path = AGENT_DATA_DIR / "replay.py"
        script_path.write_text(script_content, encoding='utf-8')
        logger.info("Saved replay script")
        
        logger.info(f"Uploading to {selected_port}...")
        cmd = [sys.executable, "-m", "mpremote", "connect", selected_port, "cp", str(script_path.absolute()), ":replay.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            error = result.stderr if result else "Unknown error"
            logger.error(f"Upload failed: {error}")
            return jsonify({"error": f"Upload failed: {error[:100]}"}), 500
        
        logger.info("Script uploaded")
        
        if auto_run:
            logger.info(f"Auto-executing on {selected_port}...")
            exec_cmd = [sys.executable, "-m", "mpremote", "connect", selected_port, "exec", "exec(open('replay.py').read())"]
            
            try:
                exec_result = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=600)
                
                if exec_result.returncode == 0:
                    output = exec_result.stdout if exec_result.stdout else "Script executed successfully"
                    logger.info("Script execution completed successfully")
                    
                    return jsonify({
                        "status": "success",
                        "message": "Script uploaded and executed",
                        "output": output,
                        "executed": True
                    })
                else:
                    error_msg = exec_result.stderr if exec_result.stderr else "Unknown error"
                    logger.error(f"Script execution failed: {error_msg}")
                    return jsonify({
                        "status": "success",
                        "message": "Script uploaded (but execution failed)",
                        "error": f"Execution failed: {error_msg[:100]}",
                        "executed": False
                    })
            except subprocess.TimeoutExpired:
                logger.error("Script execution timed out")
                return jsonify({
                    "status": "success",
                    "message": "Script uploaded and execution started",
                    "executed": True
                })
        else:
            return jsonify({
                "status": "success",
                "message": "Script uploaded to robot",
                "executed": False
            })
    
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/agent/run", methods=["POST"])
def agent_run():
    """Execute replay script on robot"""
    try:
        data = request.get_json()
        selected_port = data.get("com_port", COM_PORT)
        
        logger.info(f"Run request received for port {selected_port}")
        logger.info("Executing replay script on robot...")
        
        cmd = [sys.executable, "-m", "mpremote", "connect", selected_port, "exec", "exec(open('replay.py').read())"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            logger.info(f"Command return code: {result.returncode}")
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else (result.stdout if result.stdout else "Unknown error")
                logger.error(f"Script execution failed: {error_msg}")
                return jsonify({"error": f"Execution failed: {error_msg[:200]}"}), 500
            
            output = result.stdout if result.stdout else "Script executed successfully"
            logger.info("Script execution completed successfully")
            
            return jsonify({
                "status": "success",
                "message": "Script executed",
                "output": output
            }), 200
        
        except subprocess.TimeoutExpired:
            logger.error("Script execution timed out")
            return jsonify({"error": "Script execution timed out"}), 500
        except Exception as e:
            logger.error(f"Subprocess error: {e}")
            return jsonify({"error": f"Execution error: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"Run failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    logger.info("")
    logger.info("=" * 70)
    logger.info("FLL ROBOT TRACKER - LOCAL AGENT")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Data Directory: " + str(AGENT_DATA_DIR))
    logger.info("Log Directory: " + str(LOG_DIR))
    logger.info("")
    logger.info("Starting Flask server on http://0.0.0.0:5001")
    logger.info("Running on http://127.0.0.1:5001")
    logger.info("")
    logger.info("This agent:")
    logger.info("  - Detects serial ports on your computer")
    logger.info("  - Communicates with LEGO robots via USB")
    logger.info("  - Uploads and runs code on robots")
    logger.info("")
    logger.info("Website can now access your ports!")
    logger.info("Keep this terminal open while using the website.")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")
    
    # Run Flask
    app.run(host="0.0.0.0", port=5001, debug=False)