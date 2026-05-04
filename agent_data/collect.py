# collect_data_2_0.py - FLL Robot Data Logger v2.0

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
    """Load robot config from hub - simplified JSON parsing"""
    try:
        with open("/flash/robot_config.json", "r") as f:
            content = f.read()
            config = {}
            
            # Simple parsing - look for motor assignments
            config["motors"] = {}
            
            # Check which motors are configured
            for motor_letter in ["A", "B", "C"]:
                if f'"{motor_letter}"' in content:
                    config["motors"][motor_letter] = motor_letter  # Mark as enabled
            
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

# ============================================================
# DYNAMIC HEADER GENERATION
# ============================================================

def generate_header(config):
    """Generate CSV header based on config"""
    fields = ["time_ms"]
    
    # Motors
    for port in ["A", "B", "C", "D", "E", "F"]:
        if port in config.get("motors", {}):
            fields.append(f"motor{port}_rel_deg")
            fields.append(f"motor{port}_abs_deg")
    
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
            print("Recording started")
            await runloop.sleep_ms(200)
        if button.pressed(button.RIGHT) > 0 and recording:
            recording = False
            light_matrix.write("STP")
            print("Recording stopped")
            break
        await runloop.sleep_ms(50)

async def collect_data():
    global recording, header_sent
    f = None
    start_time = time.ticks_ms()
    
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
                    
                    # Reset motor positions
                    for port_letter in config["motors"].keys():
                        try:
                            motor.reset_relative_position(PORT_MAP[port_letter], 0)
                        except:
                            pass
                    
                    start_time = time.ticks_ms()
                    header_sent = True

                # Collect data
                t = time.ticks_ms() - start_time
                data_line = str(t)

                # Motor data
                for port in ["A", "B", "C", "D", "E", "F"]:
                    if port in config.get("motors", {}):
                        try:
                            port_obj = PORT_MAP[port]
                            rel = safe_read(lambda p=port_obj: motor.relative_position(p), 0)
                            abs_pos = safe_read(lambda p=port_obj: motor.absolute_position(p), 0)
                            data_line += f",{int(rel)},{int(abs_pos)}"
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

                await runloop.sleep_ms(150)
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

# ============================================================
# MAIN
# ============================================================

light_matrix.write("RDY")
print("FLL Robot Logger v2.0")
print(f"Motors: {list(config['motors'].keys())}")
print(f"Ready to record")

runloop.run(listen_for_buttons(), collect_data())