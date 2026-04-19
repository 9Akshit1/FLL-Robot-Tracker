# collect_data_2_0.py

import motor
import force_sensor
import distance_sensor
import time
import runloop
from hub import port, motion_sensor, light_matrix, button
import os

CSV_PATH = "/flash/data_log.csv"

PORT_MAP = {
    "A": port.A, "B": port.B, "C": port.C,
    "D": port.D, "E": port.E, "F": port.F,
}

# ============================================================
# CONFIG LOADING
# ============================================================

def load_config():
    """Load robot config from hub"""
    try:
        with open("/flash/robot_config.json", "r") as f:
            content = f.read()
            # Simple JSON parsing for MicroPython
            config = {}
            
            # Parse motors
            config["motors"] = {}
            for motor_key in ["A", "B", "C"]:
                if f'"{motor_key}"' in content:
                    config["motors"][motor_key] = True
            
            # Parse sensors
            config["sensors"] = {}
            if '"distance"' in content:
                for port_char in ["A", "B", "C", "D", "E", "F"]:
                    if f'distance": "{port_char}"' in content:
                        config["sensors"]["distance"] = port_char
            if '"force"' in content:
                for port_char in ["A", "B", "C", "D", "E", "F"]:
                    if f'force": "{port_char}"' in content:
                        config["sensors"]["force"] = port_char
            if '"color"' in content:
                for port_char in ["A", "B", "C", "D", "E", "F"]:
                    if f'color": "{port_char}"' in content:
                        config["sensors"]["color"] = port_char
            
            print("#Config loaded from hub")
            return config
    except:
        # Default fallback
        return {
            "motors": {"A": True, "B": True, "C": True},
            "sensors": {"distance": "D", "force": "F"}
        }

# ============================================================
# DYNAMIC HEADER GENERATION
# ============================================================

def generate_header(config):
    """Generate CSV header based on config"""
    fields = ["time_ms"]
    
    # Motors
    for motor_key in ["A", "B", "C"]:
        if motor_key in config["motors"]:
            fields.append(f"motor{motor_key}_rel_deg")
            fields.append(f"motor{motor_key}_abs_deg")
    
    # Sensors
    if "distance" in config["sensors"] and config["sensors"]["distance"]:
        fields.append(f"distance_{config['sensors']['distance']}_mm")
    if "force" in config["sensors"] and config["sensors"]["force"]:
        fields.append(f"force_{config['sensors']['force']}_N")
    if "color" in config["sensors"] and config["sensors"]["color"]:
        fields.append(f"color_{config['sensors']['color']}")
    
    # IMU
    fields.extend(["yaw_deg", "pitch_deg", "roll_deg"])
    
    return ",".join(fields)

# ============================================================
# DATA COLLECTION
# ============================================================

recording = False
header_sent = False
config = load_config()

def safe_read(func, default=0):
    try:
        return func()
    except:
        return default

async def listen_for_buttons():
    global recording, header_sent
    while True:
        if button.pressed(button.LEFT) > 0 and not recording:
            recording = True
            header_sent = False
            light_matrix.write("REC")
            print("#Recording started")
            await runloop.sleep_ms(200)
        if button.pressed(button.RIGHT) > 0 and recording:
            recording = False
            light_matrix.write("STP")
            print("#Recording stopped")
            break
        await runloop.sleep_ms(50)

async def collect_data():
    global recording, header_sent
    f = None
    start_time = time.ticks_ms()
    
    try:
        try:
            os.remove(CSV_PATH)
        except:
            pass
        f = open(CSV_PATH, "w")
    except:
        light_matrix.write("ERR")
        return

    try:
        while True:
            if recording:
                if not header_sent:
                    header = generate_header(config)
                    f.write(header + "\n")
                    f.flush()
                    print(header)
                    
                    for motor_key in config["motors"].keys():
                        motor.reset_relative_position(PORT_MAP[motor_key], 0)
                    
                    start_time = time.ticks_ms()
                    header_sent = True

                t = time.ticks_ms() - start_time
                data_line = str(t)

                # Collect motor data
                for motor_key in ["A", "B", "C"]:
                    if motor_key in config["motors"]:
                        port_obj = PORT_MAP[motor_key]
                        rel = safe_read(lambda p=port_obj: motor.relative_position(p), 0)
                        abs_pos = safe_read(lambda p=port_obj: motor.absolute_position(p), 0)
                        data_line += f",{int(rel)},{int(abs_pos)}"

                # Collect sensor data
                if "distance" in config["sensors"] and config["sensors"]["distance"]:
                    port_obj = PORT_MAP[config["sensors"]["distance"]]
                    dist = safe_read(lambda p=port_obj: distance_sensor.distance(p), 0)
                    data_line += f",{int(dist)}"

                if "force" in config["sensors"] and config["sensors"]["force"]:
                    port_obj = PORT_MAP[config["sensors"]["force"]]
                    force = safe_read(lambda p=port_obj: force_sensor.force(p), 0)
                    data_line += f",{int(force)}"

                if "color" in config["sensors"] and config["sensors"]["color"]:
                    port_obj = PORT_MAP[config["sensors"]["color"]]
                    color = safe_read(lambda p=port_obj: distance_sensor.distance(p), 0)
                    data_line += f",{int(color)}"

                # IMU
                yaw, pitch, roll = motion_sensor.tilt_angles()
                data_line += f",{yaw/10},{pitch/10},{roll/10}\n"

                f.write(data_line)
                f.flush()
                print(data_line.strip())

                await runloop.sleep_ms(150)
            else:
                if header_sent and not recording:
                    break
                await runloop.sleep_ms(100)
    finally:
        if f:
            f.close()
        try:
            os.sync()
        except:
            pass
        time.sleep_ms(500)

light_matrix.write("RDY")
print("#FLL Robot Logger v2.0")
print(f"#Motors: {list(config['motors'].keys())}")
print(f"#Sensors: {config['sensors']}")

runloop.run(listen_for_buttons(), collect_data())