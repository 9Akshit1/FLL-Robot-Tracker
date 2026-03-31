import motor
import time
import runloop
from hub import port, motion_sensor, light_matrix

# These MUST be at module level before the async functions
recording = False
header_sent = False
start_flag = False
stop_flag = False

CSV_PATH = "/flash/data_log.csv"

# ---------------- HELPER ----------------
def send_header(f):
    f.write(    
        "time_ms,"
        "motorA_rel_deg,motorA_abs_deg,"
        "motorB_rel_deg,motorB_abs_deg,"
        "motorC_rel_deg,motorC_abs_deg,"
        "yaw_deg,pitch_deg,roll_deg\n"
    )
    f.flush()

# ---------------- LISTEN FOR COMMANDS ----------------
async def listen_for_commands():
    """
    Polls global variables for commands:
    start_flag = True -> start recording
    stop_flag = True -> stop recording
    """
    global recording, header_sent, start_flag, stop_flag
    f = None

    try:
        f = open(CSV_PATH, "w")
    except Exception as e:
        light_matrix.write("ERR")
        print("#ERROR: cannot open CSV file:", e)
        return

    while True:
        if start_flag:
            recording = True
            header_sent = False
            light_matrix.write("REC")
            print("#Recording started")
            start_flag = False

        if stop_flag:
            recording = False
            light_matrix.write("STOP")
            print("#Recording stopped")
            if f:
                f.close()
            print("#Exiting")
            break

        await runloop.sleep_ms(100)

# ---------------- COLLECT DATA ----------------
async def collect_data():
    """
    Collects motor + IMU data and writes directly to CSV on the hub.
    """
    global recording, header_sent
    f = None
    sample_interval = 150  # ms
    start_time = time.ticks_ms()

    try:
        f = open(CSV_PATH, "a")
    except Exception as e:
        light_matrix.write("ERR")
        print("#ERROR: cannot open CSV file:", e)
        return

    while True:
        if recording:
            if not header_sent:
                send_header(f)
                motor.reset_relative_position(port.A, 0)
                motor.reset_relative_position(port.B, 0)
                motor.reset_relative_position(port.C, 0)
                start_time = time.ticks_ms()
                header_sent = True
                print("#Header written, recording data...")

            t = time.ticks_ms() - start_time

            # Motor positions
            a_rel = motor.relative_position(port.A)
            a_abs = motor.absolute_position(port.A)
            b_rel = motor.relative_position(port.B)
            b_abs = motor.absolute_position(port.B)
            c_rel = motor.relative_position(port.C)
            c_abs = motor.absolute_position(port.C)

            # IMU
            yaw, pitch, roll = motion_sensor.tilt_angles()
            yaw /= 10
            pitch /= 10
            roll /= 10

            # Write CSV line
            f.write(
                f"{t},{a_rel},{a_abs},{b_rel},{b_abs},{c_rel},{c_abs},{yaw},{pitch},{roll}\n"
            )
            f.flush()

            await runloop.sleep_ms(sample_interval)
        else:
            await runloop.sleep_ms(100)

# ---------------- MAIN ----------------
light_matrix.write("READY")
print("#FLL Robot Data Logger READY")
print("#Waiting for start_flag = True")

runloop.run(listen_for_commands(), collect_data())