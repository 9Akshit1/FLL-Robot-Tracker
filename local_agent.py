#!/usr/bin/env python3
"""
Title: local_agent.py
Course: ICS4U-02
Author: Akshit Erukulla & Rick He
Summary: Single-file bootstrap that handles everything automatically.
- Just download this file and run it. No manual setup needed.
"""

import os
import sys
import subprocess
import shutil
import time

# --- SELF-BOOTSTRAP LOGIC ---
def bootstrap():
    """Create venv and install dependencies automatically"""
    venv_dir = os.path.join(os.getcwd(), "venv")
    
    # Check if we are already running inside the venv
    is_venv = sys.prefix != sys.base_prefix
    
    if not is_venv:
        print("\n" + "="*70)
        print("FLL ROBOT TRACKER - LOCAL AGENT")
        print("="*70 + "\n")
        
        if not os.path.exists(venv_dir):
            print("[1/4] Creating virtual environment...")
            try:
                subprocess.check_call([sys.executable, "-m", "venv", "venv"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("      ✓ Virtual environment created\n")
            except subprocess.CalledProcessError as e:
                print(f"      ✗ ERROR: Failed to create venv: {e}")
                sys.exit(1)
        else:
            print("[1/4] Using existing virtual environment\n")
        
        # Determine pip path
        if os.name == 'nt':  # Windows
            pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
            python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        else:  # macOS / Linux
            pip_exe = os.path.join(venv_dir, "bin", "pip")
            python_exe = os.path.join(venv_dir, "bin", "python")
        
        # Step 2: Upgrade pip
        print("[2/4] Upgrading pip...")
        max_retries = 2
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    [python_exe, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
                    timeout=120,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("      ✓ pip upgraded\n")
                    break
                else:
                    if attempt == max_retries - 1:
                        print("      ⚠ pip upgrade had issues, continuing...\n")
                    else:
                        time.sleep(2)
            except Exception as e:
                if attempt == max_retries - 1:
                    print("      ⚠ Could not upgrade pip, continuing...\n")
                else:
                    time.sleep(2)
        
        # Step 3: Install dependencies
        print("[3/4] Installing dependencies (flask, pyserial, mpremote)...")
        print("      This may take 2-3 minutes on first run...")
        
        packages = ["flask", "pyserial", "mpremote"]
        for package in packages:
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    result = subprocess.run(
                        [python_exe, "-m", "pip", "install", package, "--quiet"],
                        timeout=120,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"      ✓ {package} installed")
                        break
                    else:
                        if attempt == max_retries - 1:
                            print(f"      ✗ ERROR: Failed to install {package}")
                            print(f"      {result.stderr[:100]}")
                            sys.exit(1)
                        else:
                            time.sleep(2)
                except subprocess.TimeoutExpired:
                    if attempt == max_retries - 1:
                        print(f"      ✗ ERROR: Installation of {package} timed out")
                        sys.exit(1)
                    else:
                        time.sleep(2)
                except Exception as e:
                    print(f"      ✗ ERROR: Failed to install {package}: {e}")
                    sys.exit(1)
        
        print("      ✓ All dependencies installed\n")
        
        # Step 4: Verify mpremote
        print("[4/4] Verifying mpremote...")
        try:
            result = subprocess.run(
                [python_exe, "-m", "mpremote", "--version"],
                timeout=10,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                print(f"      ✓ mpremote ready ({version[:50]})\n")
            else:
                print("      ⚠ mpremote verification skipped, continuing...\n")
        except Exception as e:
            print("      ⚠ mpremote verification skipped, continuing...\n")
        
        print("="*70)
        print("Starting agent...")
        print("="*70 + "\n")
        
        # Re-execute in venv
        try:
            os.execv(python_exe, [python_exe, __file__])
        except Exception as e:
            print(f"ERROR: Failed to re-execute in venv: {e}")
            sys.exit(1)

# Run bootstrap BEFORE any other imports
bootstrap()

# ============================================================
# NOW RUNNING IN VENV - IMPORT FLASK AND RUN AGENT
# ============================================================

from flask import Flask, request, jsonify
from pathlib import Path
import json
import logging
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

COM_PORT = os.getenv("COM_PORT", "COM3")
AGENT_DATA_DIR = Path("./agent_data")
AGENT_DATA_DIR.mkdir(exist_ok=True)

LOG_DIR = AGENT_DATA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Setup logging with UTF-8 encoding for Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"agent_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
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
    """Detect available serial ports on this computer"""
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
# MPREMOTE EXECUTION HELPER
# ============================================================

def run_mpremote(args, timeout=30):
    """
    Run mpremote command using Python module execution (most reliable).
    
    Args:
        args: List of command arguments (without 'mpremote' prefix)
        timeout: Command timeout in seconds
    
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        cmd = [sys.executable, "-m", "mpremote"] + args
        logger.debug(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        success = result.returncode == 0
        
        return success, result.stdout or "", result.stderr or ""
    
    except subprocess.TimeoutExpired:
        logger.error(f"mpremote command timed out after {timeout}s")
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        logger.error(f"Error running mpremote: {e}")
        return False, "", str(e)

# ============================================================
# HEALTH CHECK ENDPOINTS (REQUIRED BY DASHBOARD)
# ============================================================

@app.route("/agent/ping", methods=["GET"])
def ping():
    """Health check endpoint - required by dashboard.js"""
    logger.debug("Ping received")
    return jsonify({
        "status": "ok",
        "message": "Agent is running"
    }), 200

@app.route("/agent/status", methods=["GET"])
def agent_status():
    """Agent status endpoint - required by app.py"""
    logger.debug("Status check received")
    return jsonify({
        "status": "connected",
        "message": "Agent is running",
        "agent": "FLL Robot Tracker - Local Agent",
        "version": "1.0"
    }), 200

@app.route("/agent/info", methods=["GET"])
def agent_info():
    """Get agent information"""
    return jsonify({
        "agent": "FLL Robot Tracker - Local Agent",
        "version": "1.0",
        "data_dir": str(AGENT_DATA_DIR),
        "status": "running"
    })

# ============================================================
# PORT DETECTION ENDPOINT
# ============================================================

@app.route("/agent/detect_ports", methods=["GET"])
def detect_ports_endpoint():
    """
    Detect available serial ports on this computer.
    Required by dashboard.js
    """
    logger.info("Port detection requested")
    try:
        ports = detect_serial_ports()
        logger.info(f"Found {len(ports)} serial port(s)")
        return jsonify({
            "status": "success",
            "ports": ports
        }), 200
    except Exception as e:
        logger.error(f"Port detection failed: {e}", exc_info=True)
        return jsonify({"error": str(e), "ports": []}), 500

# ============================================================
# CONFIGURATION ENDPOINT
# ============================================================

@app.route("/agent/config", methods=["POST"])
def agent_config():
    """
    Upload robot configuration to the agent.
    Saves it locally for reference.
    """
    logger.info("Config upload request received")
    
    try:
        data = request.get_json()
        if not data or not data.get("config"):
            return jsonify({"error": "config data required"}), 400
        
        config_data = data["config"]
        
        # Save config with UTF-8 encoding
        config_path = AGENT_DATA_DIR / "robot_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        
        logger.info(f"Config saved to {config_path}")
        
        return jsonify({
            "status": "success",
            "message": "Configuration saved to local agent"
        }), 200
    
    except Exception as e:
        logger.error(f"Config upload failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# DATA COLLECTION ENDPOINTS
# ============================================================

@app.route("/agent/connect", methods=["POST"])
def agent_connect():
    """
    Receive and upload data collection script to robot.
    
    Expected JSON:
        {
            "script_content": "...",
            "com_port": "COM3"
        }
    """
    logger.info("Connect request received")
    
    try:
        data = request.get_json()
        
        # Support both field names
        script_content = data.get("script_content") or data.get("script")
        selected_port = data.get("com_port", COM_PORT)
        
        if not script_content:
            logger.error("Script content not provided")
            return jsonify({"error": "script_content required"}), 400
        
        logger.info(f"Received collection script ({len(script_content)} bytes)")
        
        # Save script locally
        script_path = AGENT_DATA_DIR / "collect.py"
        script_path.write_text(script_content, encoding='utf-8')
        logger.info(f"Saved collection script to {script_path}")
        
        # Upload to robot as main.py
        logger.info(f"Uploading to {selected_port}...")
        success, stdout, stderr = run_mpremote(
            ["connect", selected_port, "cp", str(script_path.absolute()), ":main.py"],
            timeout=15
        )
        
        if not success:
            logger.error(f"Upload failed: {stderr}")
            return jsonify({
                "status": "error",
                "message": f"Upload failed: {stderr[:200]}",
                "error": stderr[:200]
            }), 500
        
        logger.info("Script uploaded successfully")
        time.sleep(1)
        
        # Execute script on robot
        logger.info(f"Executing on {selected_port}...")
        success, stdout, stderr = run_mpremote(
            ["connect", selected_port, "exec", "exec(open('main.py').read())"],
            timeout=900
        )
        
        if not success:
            logger.warning(f"Execution had issues: {stderr}")
            # Still return success if upload worked
            return jsonify({
                "status": "success",
                "message": "Script uploaded successfully",
                "warning": stderr[:200] if stderr else None
            }), 200
        
        logger.info("Collection script executed successfully")
        
        return jsonify({
            "status": "success",
            "message": "Collection script uploaded and executed"
        }), 200
    
    except Exception as e:
        logger.error(f"Connect failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/agent/pull", methods=["POST", "GET"])
def agent_pull():
    """
    Pull CSV data from robot.
    
    Expected JSON (POST):
        {"com_port": "COM3"}
    """
    logger.info("Pull CSV request received")
    
    try:
        data = request.get_json(silent=True) or {}
        selected_port = data.get("com_port", COM_PORT)
        
        csv_path = AGENT_DATA_DIR / "data_log.csv"
        
        logger.info(f"Pulling CSV from {selected_port}...")
        success, stdout, stderr = run_mpremote(
            ["connect", selected_port, "cp", ":data_log.csv", str(csv_path.absolute())],
            timeout=30
        )
        
        if not success:
            logger.error(f"Pull failed: {stderr}")
            return jsonify({"error": f"Pull failed: {stderr[:200]}"}), 500
        
        if not csv_path.exists():
            logger.error("CSV file not found after pull")
            return jsonify({"error": "CSV file not created"}), 500
        
        # Read CSV with UTF-8 encoding
        csv_content = csv_path.read_text(encoding='utf-8', errors='ignore')
        csv_size = csv_path.stat().st_size
        
        logger.info(f"CSV pulled ({csv_size} bytes)")
        
        return jsonify({
            "status": "success",
            "csv_size": csv_size,
            "csv_content": csv_content,
            "message": "CSV pulled successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Pull failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# REPLAY SCRIPT ENDPOINTS
# ============================================================

@app.route("/agent/upload", methods=["POST"])
def agent_upload():
    """
    Upload and optionally execute replay script.
    
    Expected JSON:
        {
            "script": "...",
            "com_port": "COM3",
            "auto_run": false
        }
    """
    logger.info("Upload script request received")
    
    try:
        data = request.get_json()
        
        # Support both field names
        script_content = data.get("script") or data.get("script_content")
        selected_port = data.get("com_port", COM_PORT)
        auto_run = data.get("auto_run", False)
        
        if not script_content:
            logger.error("Script content not provided")
            return jsonify({"error": "script required"}), 400
        
        # Save replay script
        script_path = AGENT_DATA_DIR / "replay.py"
        script_path.write_text(script_content, encoding='utf-8')
        logger.info("Saved replay script")
        
        # Upload to robot
        logger.info(f"Uploading to {selected_port}...")
        success, stdout, stderr = run_mpremote(
            ["connect", selected_port, "cp", str(script_path.absolute()), ":replay.py"],
            timeout=15
        )
        
        if not success:
            logger.error(f"Upload failed: {stderr}")
            return jsonify({"error": f"Upload failed: {stderr[:200]}"}), 500
        
        logger.info("Script uploaded successfully")
        
        # Execute if requested
        if auto_run:
            logger.info(f"Executing on {selected_port}...")
            success, stdout, stderr = run_mpremote(
                ["connect", selected_port, "exec", "exec(open('replay.py').read())"],
                timeout=600
            )
            
            if success:
                logger.info("Script executed successfully")
                return jsonify({
                    "status": "success",
                    "message": "Script uploaded and executed",
                    "output": stdout or "Executed successfully",
                    "executed": True
                }), 200
            else:
                logger.warning(f"Execution failed: {stderr}")
                return jsonify({
                    "status": "success",
                    "message": "Script uploaded (execution failed)",
                    "error": stderr[:200],
                    "executed": False
                }), 200
        else:
            return jsonify({
                "status": "success",
                "message": "Script uploaded to robot",
                "executed": False
            }), 200
    
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/agent/run", methods=["POST"])
def agent_run():
    """
    Execute the replay script on the robot.
    
    Expected JSON:
        {"com_port": "COM3"}
    """
    logger.info("Run request received")
    
    try:
        data = request.get_json() or {}
        selected_port = data.get("com_port", COM_PORT)
        
        logger.info(f"Executing replay script on {selected_port}...")
        
        success, stdout, stderr = run_mpremote(
            ["connect", selected_port, "exec", "exec(open('replay.py').read())"],
            timeout=600
        )
        
        if not success:
            logger.error(f"Execution failed: {stderr}")
            return jsonify({"error": f"Execution failed: {stderr[:200]}"}), 500
        
        logger.info("Script execution completed")
        
        return jsonify({
            "status": "success",
            "message": "Script executed",
            "output": stdout or "Script executed successfully"
        }), 200
    
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
    logger.info(f"Data Directory:     {AGENT_DATA_DIR.absolute()}")
    logger.info(f"Log Directory:      {LOG_DIR.absolute()}")
    logger.info(f"Python Executable:  {sys.executable}")
    logger.info("")
    logger.info("Starting Flask server...")
    logger.info("")
    logger.info("Agent will run on:")
    logger.info("  - http://0.0.0.0:5001  (all network interfaces)")
    logger.info("  - http://127.0.0.1:5001 (localhost)")
    logger.info("")
    logger.info("Features:")
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
    try:
        app.run(host="0.0.0.0", port=5001, debug=False)
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
