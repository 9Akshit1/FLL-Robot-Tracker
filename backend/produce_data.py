# ============================================================
# produce_data.py - FIXED VERSION
# ============================================================

import motor
import time
import runloop
from hub import port, motion_sensor, light_matrix, button
import os

# Note: Removed blocking sleep - it prevents runloop from starting.
# Motor subsystem initializes quickly enough without delay.

# ---------------- CONFIG ----------------
CSV_PATH     = "/flash/data_log.csv"
CONTROL_FILE = "/flash/control.txt"

# Map port letters to hub port objects
PORT_MAP = {
    "A": port.A,
    "B": port.B,
    "C": port.C,
    "D": port.D,
    "E": port.E,
    "F": port.F,
}

# Read port config from hub_config.txt if it exists, else use defaults
MOTOR_A = port.A
MOTOR_B = port.B
MOTOR_C = port.C

try:
    with open("/flash/hub_config.txt") as f:
        for line in f:
            line = line.strip()
            if line.startswith("MOTOR_A="):
                MOTOR_A = PORT_MAP.get(line.split("=")[1].strip(), port.A)
            elif line.startswith("MOTOR_B="):
                MOTOR_B = PORT_MAP.get(line.split("=")[1].strip(), port.B)
            elif line.startswith("MOTOR_C="):
                MOTOR_C = PORT_MAP.get(line.split("=")[1].strip(), port.C)
except:
    pass  # Use defaults if file missing

recording = False
header_sent = False

# ---------------- HELPER ----------------
def send_header(f):
    header = (
        "time_ms,"
        "motorA_rel_deg,motorA_abs_deg,"
        "motorB_rel_deg,motorB_abs_deg,"
        "motorC_rel_deg,motorC_abs_deg,"
        "yaw_deg,pitch_deg,roll_deg"
    )

    f.write(header + "\n")
    f.flush()

    # 🔥 ALSO send to computer
    print(header)

def read_control_file():
    try:
        # MicroPython doesn't have os.path.exists(), use os.stat() instead
        try:
            os.stat(CONTROL_FILE)
        except OSError:
            return None  # File doesn't exist
        
        with open(CONTROL_FILE, 'r') as f:
            cmd = f.read().strip().upper()
        try:
            os.remove(CONTROL_FILE)
        except:
            pass
        return cmd
    except:
        pass
    return None

# ---------------- LISTEN FOR COMMANDS ----------------
async def listen_for_commands():
    global recording, header_sent

    while True:
        cmd = read_control_file()
        is_right_pressed = button.pressed(button.RIGHT)
        is_left_pressed  = button.pressed(button.LEFT)

        if cmd == "START" or is_right_pressed:
            if not recording:
                recording = True
                header_sent = False
                light_matrix.write("REC")
                print("#Recording started")
                await runloop.sleep_ms(200)

        elif cmd == "STOP" or is_left_pressed:
            if recording:
                recording = False
                light_matrix.write("STP")
                print("#Recording stopped. Exiting...")
                break

        await runloop.sleep_ms(50)

# ---------------- COLLECT DATA ----------------
async def collect_data():
    global recording, header_sent
    f = None
    sample_interval = 150
    start_time = time.ticks_ms()

    try:
        # Delete old CSV file to start fresh (avoid duplicate headers)
        # Do this ONCE at startup
        try:
            os.remove(CSV_PATH)
            print("#Deleted old CSV file")
        except:
            print("#No old CSV file found")
        f = open(CSV_PATH, "w")
    except Exception as e:
        light_matrix.write("ERR")
        print("#ERROR: cannot open CSV file:", e)
        return

    try:
        while True:
            if recording:
                if not header_sent:
                    send_header(f)
                    motor.reset_relative_position(MOTOR_A, 0)
                    motor.reset_relative_position(MOTOR_B, 0)
                    motor.reset_relative_position(MOTOR_C, 0)
                    start_time = time.ticks_ms()
                    header_sent = True
                    print("#Header written, recording data...")

                t = time.ticks_ms() - start_time

                a_rel = motor.relative_position(MOTOR_A)
                a_abs = motor.absolute_position(MOTOR_A)
                b_rel = motor.relative_position(MOTOR_B)
                b_abs = motor.absolute_position(MOTOR_B)
                c_rel = motor.relative_position(MOTOR_C)
                c_abs = motor.absolute_position(MOTOR_C)

                yaw, pitch, roll = motion_sensor.tilt_angles()

                data_line = "{},{},{},{},{},{},{},{},{},{}\n".format(
                    t, a_rel, a_abs, b_rel, b_abs, c_rel, c_abs,
                    yaw/10, pitch/10, roll/10
                )

                f.write(data_line)
                f.flush()
                print(data_line.strip())

                await runloop.sleep_ms(sample_interval)
            else:
                if header_sent and not recording:
                    break
                await runloop.sleep_ms(100)
    finally:
        if f:
            f.close()
            print("#File closed safely.")
        # CRITICAL: Force sync to disk before exit
        # This ensures data persists even if hub reboots during auto-run
        try:
            os.sync()
        except:
            pass
        time.sleep_ms(500)

# ---------------- MAIN ----------------
light_matrix.write("RDY")
print("#FLL Robot Data Logger READY")
print("#Right Button or START command to begin")
print("#Left Button or STOP command to end")

runloop.run(listen_for_commands(), collect_data())