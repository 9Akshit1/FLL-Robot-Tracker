import motor
import time
import runloop
from hub import port

PORT_MAP = {
    "A": port.A,
    "B": port.B,
    "C": port.C,
}

timeline = [{'delay': 71, 'motors': {'A': (-288, 647), 'B': (276, 535)}}, {'delay': 72, 'motors': {'A': (-301, 361), 'B': (287, 305)}}, {'delay': 76, 'motors': {'A': (-428, 750), 'B': (401, 750)}}, {'delay': 76, 'motors': {'A': (-467, 750), 'B': (441, 750)}}, {'delay': 76, 'motors': {'A': (-484, 447), 'B': (457, 421)}}, {'delay': 78, 'motors': {'A': (-495, 153)}}, {'delay': 79, 'motors': {'A': (-506, 278)}}, {'delay': 80, 'motors': {'A': (-515, 225)}}, {'delay': 79, 'motors': {'A': (-537, 455)}}, {'delay': 607, 'motors': {'A': (-625, 289), 'B': (453, 32)}}, {'delay': 83, 'motors': {'C': (19, 289)}}, {'delay': 85, 'motors': {'C': (38, 447)}}, {'delay': 84, 'motors': {'C': (55, 404)}}, {'delay': 84, 'motors': {'C': (73, 428)}}, {'delay': 86, 'motors': {'C': (89, 372)}}, {'delay': 86, 'motors': {'C': (106, 395)}}, {'delay': 86, 'motors': {'C': (121, 348)}}, {'delay': 86, 'motors': {'C': (132, 255)}}, {'delay': 86, 'motors': {'C': (152, 232)}}, {'delay': 88, 'motors': {'C': (163, 250)}}, {'delay': 88, 'motors': {'C': (171, 181)}}, {'delay': 67, 'motors': {'C': (140, 447)}}, {'delay': 603, 'motors': {'C': (71, 228)}}, {'delay': 75, 'motors': {'C': (51, 293)}}, {'delay': 74, 'motors': {'C': (37, 378)}}, {'delay': 81, 'motors': {'C': (29, 197)}}, {'delay': 75, 'motors': {'C': (14, 186)}}]

def execute_frame(motors_command):
    for port_name, (target_degrees, speed) in motors_command.items():
        if port_name in PORT_MAP:
            motor.run_for_degrees(PORT_MAP[port_name], target_degrees, speed)

async def main():
    print("Starting replay...")
    print("Total frames: " + str(len(timeline)))
    print("Motors: " + str(list(PORT_MAP.keys())))
    
    try:
        for frame_idx, frame_data in enumerate(timeline):
            delay_ms = frame_data['delay']
            motors_cmd = frame_data['motors']
            
            if not motors_cmd:
                if delay_ms > 0:
                    await runloop.sleep_ms(delay_ms)
                continue
            
            execute_frame(motors_cmd)
            
            if delay_ms > 0:
                await runloop.sleep_ms(delay_ms)
            
            if (frame_idx + 1) % 10 == 0:
                print("Frame " + str(frame_idx + 1) + "/" + str(len(timeline)))
        
        print("Replay complete!")
        
    except Exception as e:
        print("Error: " + str(e))

runloop.run(main())
