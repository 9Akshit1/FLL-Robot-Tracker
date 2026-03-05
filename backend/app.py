import os
import threading
import serial
import time
import csv
from flask import Flask, render_template, jsonify, request, send_file

from movement_analysis import run as analyze_movements
from convert_to_code import generate_spike_script

import shutil
from pathlib import Path

HUB_CSV_PATH = "/path/to/hub/data_log.csv"  # adjust if using PyBricks serial file API
LOCAL_CSV_PATH = Path("backend/data/raw_data.csv")

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)

# ---------------- CONFIG ----------------

SERIAL_PORT = "COM3"  # CHANGE THIS
BAUD_RATE = 115200

ser = None
recording = False
recorded_lines = []
serial_thread_running = False

DATA_DIR = "data"
RAW_PATH = os.path.join(DATA_DIR, "raw_data.csv")
CLEAN_PATH = os.path.join(DATA_DIR, "cleaned_data.csv")
GENERATED_PATH = os.path.join(DATA_DIR, "generated_spike.py")

os.makedirs(DATA_DIR, exist_ok=True)


# ---------------- SERIAL READER ----------------

def serial_reader():
    global recorded_lines, recording

    while serial_thread_running:
        if ser and ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()

            if recording and not line.startswith("#"):
                recorded_lines.append(line)

        time.sleep(0.01)


def connect_serial():
    global ser, serial_thread_running

    if not ser:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        serial_thread_running = True
        threading.Thread(target=serial_reader, daemon=True).start()


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/connect")
def connect():
    try:
        connect_serial()
        return jsonify({"status": "Connected to robot"})
    except Exception as e:
        return jsonify({"status": str(e)})


@app.route("/start_recording")
def start_recording():
    global recording, recorded_lines

    recorded_lines = []
    recording = True

    ser.write(b"START\n")

    return jsonify({"status": "Recording started"})


@app.route("/stop_recording")
def stop_recording():
    ser.write(b"STOP\n")  # stop recording
    time.sleep(0.5)

    # Pull the file from hub
    # Option A: If hub is connected via USB and exposes filesystem:
    shutil.copy(HUB_CSV_PATH, LOCAL_CSV_PATH)

    return jsonify({"status": "Recording stopped, CSV saved"})


@app.route("/convert")
def convert():
    # Clean if needed (optional)
    os.replace(RAW_PATH, CLEAN_PATH)

    # Run movement analysis
    analyze_movements(CLEAN_PATH)

    # Generate SPIKE replay file
    generate_spike_script(CLEAN_PATH, GENERATED_PATH)

    return jsonify({"status": "Conversion complete"})


@app.route("/download")
def download():
    return send_file(GENERATED_PATH, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)