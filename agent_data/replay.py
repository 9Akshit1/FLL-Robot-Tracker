import motor
import time
import runloop
from hub import port

PORT_MAP = {
    "A": port.A,
    "B": port.B,
    "C": port.C,
}

timeline = [{'delay': 76, 'motors': {'A': (-15, 422), 'B': (10, 281)}}, {'delay': 74, 'motors': {'A': (-17, 491), 'B': (8, 231), 'C': (-1, 28)}}, {'delay': 72, 'motors': {'A': (-15, 445), 'B': (6, 178)}}, {'delay': 74, 'motors': {'A': (-16, 462), 'B': (9, 260), 'C': (1, 28)}}, {'delay': 74, 'motors': {'A': (-16, 462), 'B': (9, 260), 'C': (-1, 28)}}, {'delay': 77, 'motors': {'A': (-17, 472), 'B': (8, 222), 'C': (1, 27)}}, {'delay': 73, 'motors': {'A': (-15, 439), 'B': (5, 146), 'C': (-1, 29)}}, {'delay': 77, 'motors': {'A': (-11, 305), 'B': (1, 27), 'C': (1, 27)}}, {'delay': 76, 'motors': {'A': (-10, 281), 'C': (-1, 28)}}, {'delay': 75, 'motors': {'A': (-12, 342), 'C': (1, 28)}}, {'delay': 77, 'motors': {'A': (-11, 305), 'B': (1, 27), 'C': (-1, 27)}}, {'delay': 76, 'motors': {'A': (-10, 281), 'B': (4, 112)}}, {'delay': 76, 'motors': {'A': (-11, 309), 'B': (4, 112)}}, {'delay': 80, 'motors': {'A': (-10, 267), 'B': (7, 187), 'C': (1, 26)}}, {'delay': 80, 'motors': {'A': (-7, 187), 'B': (7, 187), 'C': (-1, 26)}}, {'delay': 79, 'motors': {'A': (-3, 81), 'B': (4, 108), 'C': (-1, 27)}}, {'delay': 80, 'motors': {'B': (1, 26)}}, {'delay': 80, 'motors': {'A': (5, 133), 'B': (-5, 133)}}, {'delay': 83, 'motors': {'A': (6, 154), 'B': (-11, 283)}}, {'delay': 80, 'motors': {'A': (26, 695), 'B': (-18, 481)}}, {'delay': 80, 'motors': {'A': (29, 750), 'B': (-25, 668)}}, {'delay': 82, 'motors': {'A': (32, 750), 'B': (-29, 750)}}, {'delay': 81, 'motors': {'A': (31, 750), 'B': (-23, 607)}}, {'delay': 84, 'motors': {'A': (33, 750), 'B': (-22, 560)}}, {'delay': 81, 'motors': {'A': (23, 607), 'B': (-13, 343)}}, {'delay': 84, 'motors': {'A': (9, 229), 'B': (-4, 101)}}, {'delay': 610, 'motors': {'A': (-6, 21), 'B': (48, 168)}}, {'delay': 87, 'motors': {'A': (-2, 49), 'B': (18, 442), 'C': (-1, 24)}}, {'delay': 83, 'motors': {'A': (-25, 644), 'B': (30, 750)}}, {'delay': 87, 'motors': {'A': (-60, 750), 'B': (56, 750), 'C': (1, 24)}}, {'delay': 86, 'motors': {'A': (-79, 750), 'B': (70, 750)}}, {'delay': 87, 'motors': {'A': (282, 750), 'B': (-283, 750)}}, {'delay': 87, 'motors': {'A': (-45, 750), 'B': (61, 750), 'C': (-1, 24)}}, {'delay': 88, 'motors': {'A': (-24, 583), 'B': (29, 705)}}, {'delay': 88, 'motors': {'A': (-6, 145), 'B': (11, 267)}}, {'delay': 91, 'motors': {'A': (1, 23), 'B': (-2, 47)}}, {'delay': 91, 'motors': {'B': (-1, 23), 'C': (25, 587)}}, {'delay': 92, 'motors': {'C': (29, 674)}}, {'delay': 93, 'motors': {'A': (2, 46), 'B': (2, 46), 'C': (31, 713)}}, {'delay': 94, 'motors': {'A': (1, 22), 'B': (-2, 45), 'C': (31, 705)}}, {'delay': 95, 'motors': {'A': (2, 45), 'B': (-1, 22), 'C': (28, 630)}}, {'delay': 95, 'motors': {'C': (8, 180)}}, {'delay': 68, 'motors': {'B': (2, 62)}}, {'delay': 68, 'motors': {'B': (2, 62)}}, {'delay': 71, 'motors': {'B': (1, 30)}}, {'delay': 76, 'motors': {'C': (-27, 750)}}, {'delay': 77, 'motors': {'C': (-31, 750)}}, {'delay': 78, 'motors': {'C': (-24, 658)}}, {'delay': 79, 'motors': {'C': (-14, 379)}}, {'delay': 77, 'motors': {'C': (-3, 83)}}, {'delay': 89, 'motors': {'C': (-16, 384)}}, {'delay': 89, 'motors': {'C': (-19, 456)}}, {'delay': 90, 'motors': {'C': (-12, 285)}}, {'delay': 89, 'motors': {'C': (-3, 72)}}, {'delay': 91, 'motors': {'C': (-2, 47)}}, {'delay': 96, 'motors': {'C': (-16, 356)}}, {'delay': 97, 'motors': {'C': (-10, 220)}}, {'delay': 95, 'motors': {'A': (1, 22), 'C': (-2, 45)}}, {'delay': 95, 'motors': {'C': (-1, 22)}}, {'delay': 74, 'motors': {'B': (1, 28), 'C': (-10, 289)}}, {'delay': 77, 'motors': {'C': (-15, 416)}}, {'delay': 75, 'motors': {'C': (-3, 85)}}, {'delay': 75, 'motors': {'C': (-1, 28)}}, {'delay': 620, 'motors': {'B': (-1, 20), 'C': (1, 10)}}, {'delay': 93, 'motors': {'A': (2, 46), 'B': (-10, 230)}}, {'delay': 91, 'motors': {'B': (2, 47)}}]

def execute_frame(motors_command):
    """Execute motors for one frame"""
    for port_name, (target_degrees, speed) in motors_command.items():
        if port_name in PORT_MAP:
            motor.run_for_degrees(PORT_MAP[port_name], target_degrees, speed)

async def main():
    print("FLL Replay")
    print("Frames: " + str(len(timeline)))

    try:
        for frame_idx, frame_data in enumerate(timeline):
            delay_ms = frame_data['delay']
            motors_cmd = frame_data['motors']

            if motors_cmd:
                execute_frame(motors_cmd)

            if delay_ms > 0:
                await runloop.sleep_ms(delay_ms)

            if (frame_idx + 1) % 10 == 0:
                print("Frame " + str(frame_idx + 1) + "/" + str(len(timeline)))

        print("Done!")

    except Exception as e:
        print("Error: " + str(e))

runloop.run(main())
