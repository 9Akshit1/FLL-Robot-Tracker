"""
Title: collect_data_2_0.py
Course: ICS4U-02
Author: Akshit Erukulla, Rick He
Summary: Logs motor positions, sensor readings, and IMU tilt angles to a CSV file on the SPIKE hub.
"""

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

def load_config():
    """
    Loads robot motor and sensor configuration from a JSON file stored on the hub.
    If loading fails, a default configuration is returned.

    Args:
        None

    Returns:
        dict: Configuration dictionary containing motor and sensor port mappings.
    """
    try:
        with open("/flash/robot_config.json", "r") as f:
            content = f.read()
            config = {}

            # Simple parsing - look for motor assignments
            config["motors"] = {}

            # Check which motors are configured
            for motor_letter in ["A", "B", "C"]:
                if f'"{motor_letter}"' in content:
                    config["motors"][motor_letter] = motor_letter

            # Parse sensors
            config["sensors"] = {}

            # Distance sensor
            if '"distance"' in content:
                for sensor_port in ["D", "E", "F"]:
                    search_str = f'distance": "{sensor_port}"'
                    if search_str in content:
                        config["sensors"]["distance"] = sensor_port
                        break

            # Force sensor
            if '"force"' in content:
                for sensor_port in ["D", "E", "F"]:
                    search_str = f'force": "{sensor_port}"'
                    if search_str in content:
                        config["sensors"]["force"] = sensor_port
                        break

            # Color sensor
            if '"color"' in content:
                for sensor_port in ["D", "E", "F"]:
                    search_str = f'color": "{sensor_port}"'
                    if search_str in content:
                        config["sensors"]["color"] = sensor_port
                        break

            print("Config loaded")
            return config
    except Exception as e:
        print(f"Config load error: {e}")
        # Default config
        return {
            "motors": {"A": "A", "B": "B", "C": "C"},
            "sensors": {"distance": "D"}
        }

def generate_header(config):
    """
    Generates a CSV header string based on the motors and sensors enabled in the config.
    The header includes absolute motor positions, calculated relative positions, sensors, and IMU angles.

    Args:
        config (dict): Configuration dictionary containing motor and sensor mappings.

    Returns:
        str: A comma-separated CSV header line.
    """
    fields = ["time_ms"]

    # Motors - FIXED: Use absolute position for reliability
    for port in ["A", "B", "C", "D", "E", "F"]:
        if port in config.get("motors", {}):
            fields.append(f"motor{port}_abs_deg")  # ← CHANGED: Use absolute
            fields.append(f"motor{port}_rel_deg")  # ← Still collect for reference

    # Sensors
    sensors = config.get("sensors", {})
    if sensors.get("distance"):
        fields.append(f"distance_{sensors['distance']}_mm")
    if sensors.get("force"):
        fields.append(f"force_{sensors['force']}_N")
    if sensors.get("color"):
        fields.append(f"color_{sensors['color']}")

    # IMU
    fields.extend(["yaw_deg", "pitch_deg", "roll_deg"])

    return ",".join(fields)

recording = False
header_sent = False
config = load_config()

def safe_read(func, default=0):
    """
    Calls a sensor/motor function safely and returns a default value if it fails.
    This prevents logging from crashing due to disconnected hardware.

    Args:
        func (callable): Function to execute (usually a motor or sensor read).
        default (any): Value returned if the function raises an exception.

    Returns:
        any: The function result if successful, otherwise the default value.
    """
    try:
        return func()
    except:
        return default

async def listen_for_buttons():
    """
    Monitors hub buttons to start and stop recording mode.
    LEFT starts recording and RIGHT stops recording.

    Args:
        None

    Returns:
        None
    """
    global recording, header_sent
    while True:
        if button.pressed(button.LEFT) > 0 and not recording:
            recording = True
            header_sent = False
            light_matrix.write("REC")
            print("Recording started")
            await runloop.sleep_ms(200)
        if button.pressed(button.RIGHT) > 0 and recording:
            recording = False
            light_matrix.write("STP")
            print("Recording stopped")
            break
        await runloop.sleep_ms(50)

async def collect_data():
    """
    Collects motor, sensor, and IMU data while recording is enabled and writes it to a CSV file.
    Motor relative position is calculated using the initial absolute motor position as the baseline.

    Args:
        None

    Returns:
        None
    """
    global recording, header_sent
    f = None
    start_time = time.ticks_ms()
    
    # Store starting absolute positions for calculating relative positions
    starting_abs_position = {}

    try:
        # Remove old file if exists
        try:
            os.remove(CSV_PATH)
        except:
            pass

        f = open(CSV_PATH, "w")
    except Exception as e:
        print(f"File open error: {e}")
        light_matrix.write("ERR")
        return

    try:
        while True:
            if recording:
                if not header_sent:
                    # Write header
                    header = generate_header(config)
                    f.write(header + "\n")
                    f.flush()
                    print(header)

                    # Store starting absolute positions
                    # These are used to calculate relative positions
                    for port_letter in config["motors"].keys():
                        try:
                            abs_pos = safe_read(
                                lambda p=PORT_MAP[port_letter]: motor.absolute_position(p),
                                0
                            )
                            starting_abs_position[port_letter] = abs_pos
                            print(f"Motor {port_letter} starting position: {abs_pos}")
                        except:
                            starting_abs_position[port_letter] = 0

                    start_time = time.ticks_ms()
                    header_sent = True

                # Collect data
                t = time.ticks_ms() - start_time
                data_line = str(t)

                # Motor data - FIXED: Use absolute position as primary
                for port in ["A", "B", "C", "D", "E", "F"]:
                    if port in config.get("motors", {}):
                        try:
                            port_obj = PORT_MAP[port]
                            
                            # PRIMARY: Use absolute position (reliable)
                            abs_pos = safe_read(lambda p=port_obj: motor.absolute_position(p), 0)
                            
                            # SECONDARY: Calculate relative from absolute
                            rel_pos = abs_pos - starting_abs_position.get(port, 0)
                            
                            data_line += f",{int(abs_pos)},{int(rel_pos)}"
                        except:
                            data_line += ",0,0"

                # Sensor data
                sensors = config.get("sensors", {})

                if sensors.get("distance"):
                    try:
                        port_obj = PORT_MAP[sensors["distance"]]
                        dist = safe_read(lambda p=port_obj: distance_sensor.distance(p), 0)
                        data_line += f",{int(dist)}"
                    except:
                        pass

                if sensors.get("force"):
                    try:
                        port_obj = PORT_MAP[sensors["force"]]
                        force = safe_read(lambda p=port_obj: force_sensor.force(p), 0)
                        data_line += f",{int(force)}"
                    except:
                        pass

                if sensors.get("color"):
                    try:
                        port_obj = PORT_MAP[sensors["color"]]
                        color = safe_read(lambda p=port_obj: distance_sensor.distance(p), 0)
                        data_line += f",{int(color)}"
                    except:
                        pass

                # IMU
                try:
                    yaw, pitch, roll = motion_sensor.tilt_angles()
                    data_line += f",{yaw/10},{pitch/10},{roll/10}\n"
                except:
                    data_line += ",0,0,0\n"

                f.write(data_line)
                f.flush()

                await runloop.sleep_ms(30)
            else:
                if header_sent and not recording:
                    break
                await runloop.sleep_ms(100)
    except Exception as e:
        print(f"Collection error: {e}")
    finally:
        if f:
            f.close()
        try:
            os.sync()
        except:
            pass
        time.sleep_ms(500)


# main
light_matrix.write("RDY")
print("FLL Robot Logger v2.0 FIXED")
print("Using absolute_position() for accurate tracking")
print(f"Motors: {list(config['motors'].keys())}")
print(f"Ready to record")

runloop.run(listen_for_buttons(), collect_data())
