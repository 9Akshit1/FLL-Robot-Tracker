#!/usr/bin/env python3
"""
FLL Robot Tracker - Local Agent

This script runs on YOUR computer and enables the web app to:
- Detect available serial ports
- Communicate with your LEGO robot via USB
- Upload and run code on the robot

===============================================================================
QUICK START (4 STEPS)
===============================================================================

Step 1: Download this file
  - Save this file as: local_agent.py

Step 2: Install dependencies
  Open a terminal/command prompt in the same folder and run:
  
  Windows:
    pip install flask pyserial mpremote
  
  Mac/Linux:
    pip3 install flask pyserial mpremote

Step 3: Run the agent
  In the same terminal, run:
  
    python local_agent.py
  
  You should see:
    Starting Flask server on http://0.0.0.0:5001
    Running on http://127.0.0.1:5001
  
  Keep this terminal open!

Step 4: Use the website
  Visit: https://aksh19.pythonanywhere.com/
  
  The website will show "Agent: Online" (green badge)
  You can now detect ports and use the app normally

===============================================================================
IMPORTANT
===============================================================================

- This agent must run on YOUR computer (not shared)
- Keep the terminal open while using the website
- The agent listens on port 5001 (local only)
- Your robot connects via USB to your computer
- Website finds the agent automatically (no IP configuration needed)

===============================================================================
TROUBLESHOOTING
===============================================================================

Agent not installing?
  - Make sure you have Python 3.7+ installed
  - Try: python -m pip install flask pyserial mpremote
  - On Mac, try: pip3 instead of pip

Agent not running?
  - Check terminal output for error messages
  - Make sure port 5001 isn't blocked by firewall
  - Windows: Allow Python through Windows Defender

Agent running but website shows "offline"?
  - Refresh the website (F5)
  - Check browser console (F12) for errors
  - Make sure agent terminal shows "Running on"

Robot not detected?
  - Make sure robot is connected via USB
  - Try: python scripts/check_ports.py (if you have it)
  - Restart agent and refresh website

===============================================================================
"""

from flask import Flask, jsonify, request
from pathlib import Path
import subprocess
import json
import time
import os
import logging
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# Get COM port from environment or default
COM_PORT = os.getenv("COM_PORT", "COM3")

# Local storage for agent data
AGENT_DATA_DIR = Path("./agent_data")
AGENT_DATA_DIR.mkdir(exist_ok=True)

# Logging
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

# Enable CORS headers for all requests
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
    """
    Detect available serial ports on this computer
    
    Returns:
        list: List of port dicts with 'port' and 'description'
    """
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
        # Fallback: return common ports
        if os.name == 'nt':  # Windows
            return [{"port": f"COM{i}", "description": "Potential Serial Port"} for i in range(1, 10)]
        else:  # Mac/Linux
            return [{"port": f"/dev/ttyUSB{i}", "description": "Potential Serial Port"} for i in range(5)]

# ============================================================
# ENDPOINTS
# ============================================================

@app.route("/agent/detect_ports")
def detect_ports():
    """
    Detect available serial ports on this computer
    
    The web app calls this to get a list of ports.
    User can then select which port to use.
    
    Returns:
        {
            "status": "success",
            "ports": [
                {"port": "COM3", "description": "Silicon Labs CP210x..."},
                {"port": "COM4", "description": "USB Serial Device"}
            ]
        }
    """
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
        "version": "1.0",
        "data_dir": str(AGENT_DATA_DIR),
        "status": "running"
    })

# ============================================================
# HELPER FUNCTION FOR ROBOT COMMUNICATION
# ============================================================

def run_mpremote(args, timeout=10):
    """
    Run mpremote command
    
    Args:
        args: List of mpremote arguments
        timeout: Command timeout in seconds
    
    Returns:
        CompletedProcess or None on error
    """
    try:
        cmd = ["mpremote", "connect", COM_PORT] + args
        logger.debug(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        logger.debug(f"Return code: {result.returncode}")
        return result
    
    except subprocess.TimeoutExpired:
        logger.error(f"mpremote timeout after {timeout}s")
        return None
    except FileNotFoundError:
        logger.error("mpremote not found - install with: pip install mpremote")
        return None
    except Exception as e:
        logger.error(f"Error running mpremote: {e}")
        return None

# ============================================================
# ROBOT COMMUNICATION ENDPOINTS
# ============================================================

@app.route("/agent/connect", methods=["POST"])
def agent_connect():
    """
    Upload collection script to robot and start recording
    
    Expects JSON:
        {
            "script_content": "import motor\n...",
            "com_port": "COM3"
        }
    
    Returns:
        {"status": "success", "message": "Recording complete"}
        {"status": "error", "error": "..."} (500)
    """
    logger.info("Connect request received")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data"}), 400
        
        script_content = data.get("script_content")
        selected_port = data.get("com_port", COM_PORT)
        
        if not script_content:
            return jsonify({"error": "script_content required"}), 400
        
        # Save script locally
        script_path = AGENT_DATA_DIR / "collect.py"
        script_path.write_text(script_content)
        logger.info(f"Saved collection script")
        
        # Upload to robot using selected port
        logger.info(f"Uploading to robot on {selected_port}...")
        cmd = ["mpremote", "connect", selected_port, "cp", str(script_path.absolute()), ":main.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            error = result.stderr if result else "Unknown error"
            logger.error(f"Upload failed: {error}")
            return jsonify({"error": f"Upload failed: {error[:100]}"}), 500
        
        logger.info("Script uploaded, executing...")
        time.sleep(1)
        
        # Execute script
        cmd = ["mpremote", "connect", selected_port, "exec", "exec(open('main.py').read())"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            logger.info("Recording complete")
            return jsonify({
                "status": "success",
                "message": "Recording complete",
                "output": result.stdout
            })
        else:
            error = result.stderr if result else "Unknown error"
            logger.error(f"Execution failed: {error}")
            return jsonify({"error": f"Execution failed: {error[:100]}"}), 500
    
    except Exception as e:
        logger.error(f"Connect failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/agent/pull", methods=["GET", "POST"])
def agent_pull():
    """
    Pull CSV data from robot
    
    Expects JSON:
        {"com_port": "COM3"}
    
    Returns:
        {
            "status": "success",
            "csv_size": 4096,
            "csv_content": "time_ms,motorA_rel_deg,...\n..."
        }
    """
    logger.info("Pull CSV request received")
    
    try:
        data = request.get_json() or {}
        selected_port = data.get("com_port", COM_PORT)
        
        csv_path = AGENT_DATA_DIR / "data_log.csv"
        
        logger.info(f"Pulling CSV from {selected_port}...")
        cmd = ["mpremote", "connect", selected_port, "cp", ":/flash/data_log.csv", str(csv_path.absolute())]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            error = result.stderr if result else "CSV not found on robot"
            logger.error(f"Pull failed: {error}")
            return jsonify({"error": f"Pull failed: {error[:100]}"}), 500
        
        if not csv_path.exists():
            logger.error("CSV file not found after pull")
            return jsonify({"error": "CSV file not created"}), 500
        
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
    """
    Upload robot configuration to the agent
    
    Expects JSON:
        {
            "config": { ... },
            "com_port": "COM3"
        }
    """
    logger.info("Config upload request received")
    
    try:
        data = request.get_json()
        if not data or not data.get("config"):
            return jsonify({"error": "config data required"}), 400
        
        config_data = data["config"]
        
        # Save config locally for reference
        config_path = AGENT_DATA_DIR / "robot_config.json"
        with open(config_path, 'w') as f:
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
    """
    Upload replay script to robot
    
    Expects JSON:
        {
            "script_content": "import runloop\n...",
            "com_port": "COM3"
        }
    """
    logger.info("Upload script request received")
    
    try:
        data = request.get_json()
        if not data or not data.get("script_content"):
            return jsonify({"error": "script_content required"}), 400
        
        script_content = data["script_content"]
        selected_port = data.get("com_port", COM_PORT)
        script_path = AGENT_DATA_DIR / "replay.py"
        script_path.write_text(script_content)
        logger.info("Saved replay script")
        
        logger.info(f"Uploading to {selected_port}...")
        cmd = ["mpremote", "connect", selected_port, "cp", str(script_path.absolute()), ":replay.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            error = result.stderr if result else "Unknown error"
            logger.error(f"Upload failed: {error}")
            return jsonify({"error": f"Upload failed: {error[:100]}"}), 500
        
        logger.info("Script uploaded")
        return jsonify({
            "status": "success",
            "message": "Script uploaded to robot"
        })
    
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/agent/run", methods=["GET", "POST"])
def agent_run():
    """
    Execute replay script on robot
    
    Expects JSON:
        {"com_port": "COM3"}
    """
    logger.info("Run script request received")
    
    try:
        data = request.get_json() or {}
        selected_port = data.get("com_port", COM_PORT)
        
        logger.info(f"Executing on {selected_port}...")
        cmd = ["mpremote", "connect", selected_port, "exec", "exec(open('replay.py').read())"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            logger.info("Script executed successfully")
            return jsonify({
                "status": "success",
                "message": "Script executed",
                "output": result.stdout if result.stdout else "Script completed"
            })
        else:
            error = result.stderr if result else "Unknown error"
            logger.error(f"Execution failed: {error}")
            return jsonify({"error": f"Execution failed: {error[:200]}"}), 500
    
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