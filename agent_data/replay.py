import motor
import runloop
from hub import port

PORT_MAP = {
    "A": port.A,
    "B": port.B,
    "C": port.C,
}

# 80 frames, ~7424ms total recorded time
# Each entry: {'delay_ms': int, 'motors': {'A': [degrees, speed], ...}}
TIMELINE = [{'delay_ms': 69, 'motors': {'A': [1, 31]}}, {'delay_ms': 67, 'motors': {'A': [1, 31], 'B': [-1, 31]}}, {'delay_ms': 67, 'motors': {'B': [1, 31]}}, {'delay_ms': 68, 'motors': {}}, {'delay_ms': 68, 'motors': {'B': [-1, 31]}}, {'delay_ms': 68, 'motors': {'B': [1, 31]}}, {'delay_ms': 68, 'motors': {'B': [3, 94]}}, {'delay_ms': 69, 'motors': {'A': [-3, 93], 'B': [6, 186]}}, {'delay_ms': 69, 'motors': {'A': [-3, 93], 'B': [5, 155]}}, {'delay_ms': 69, 'motors': {'A': [-13, 403], 'B': [14, 434]}}, {'delay_ms': 71, 'motors': {'A': [-16, 482], 'B': [23, 693]}}, {'delay_ms': 71, 'motors': {'A': [-21, 632], 'B': [23, 693]}}, {'delay_ms': 70, 'motors': {'A': [-26, 750], 'B': [25, 750]}}, {'delay_ms': 70, 'motors': {'A': [-26, 750], 'B': [24, 733]}}, {'delay_ms': 72, 'motors': {'A': [-30, 750], 'B': [19, 564], 'C': [-1, 29]}}, {'delay_ms': 70, 'motors': {'A': [331, 750], 'B': [15, 458], 'C': [1, 30]}}, {'delay_ms': 612, 'motors': {'A': [-221, 750], 'B': [64, 223]}}, {'delay_ms': 72, 'motors': {'A': [-4, 118], 'B': [5, 148]}}, {'delay_ms': 72, 'motors': {'B': [1, 29]}}, {'delay_ms': 72, 'motors': {'B': [-1, 29]}}, {'delay_ms': 73, 'motors': {}}, {'delay_ms': 73, 'motors': {}}, {'delay_ms': 73, 'motors': {}}, {'delay_ms': 74, 'motors': {}}, {'delay_ms': 74, 'motors': {}}, {'delay_ms': 74, 'motors': {}}, {'delay_ms': 75, 'motors': {'C': [4, 114]}}, {'delay_ms': 76, 'motors': {'C': [1, 28]}}, {'delay_ms': 76, 'motors': {'C': [1, 28]}}, {'delay_ms': 77, 'motors': {'C': [-1, 27]}}, {'delay_ms': 76, 'motors': {'C': [2, 56]}}, {'delay_ms': 77, 'motors': {'C': [8, 222]}}, {'delay_ms': 77, 'motors': {'C': [16, 444]}}, {'delay_ms': 77, 'motors': {'B': [-1, 27], 'C': [15, 416]}}, {'delay_ms': 77, 'motors': {'B': [1, 27], 'C': [11, 305]}}, {'delay_ms': 78, 'motors': {'C': [12, 329]}}, {'delay_ms': 78, 'motors': {'C': [12, 329]}}, {'delay_ms': 78, 'motors': {'A': [1, 27], 'C': [15, 411]}}, {'delay_ms': 79, 'motors': {'B': [-1, 27], 'C': [17, 460]}}, {'delay_ms': 80, 'motors': {'C': [16, 428]}}, {'delay_ms': 78, 'motors': {'A': [1, 27], 'C': [14, 384]}}, {'delay_ms': 80, 'motors': {'A': [1, 26], 'B': [-1, 26], 'C': [12, 321]}}, {'delay_ms': 80, 'motors': {'A': [1, 26], 'C': [8, 214]}}, {'delay_ms': 80, 'motors': {'C': [7, 187]}}, {'delay_ms': 83, 'motors': {'A': [1, 25], 'B': [1, 25], 'C': [2, 51]}}, {'delay_ms': 81, 'motors': {'B': [1, 26], 'C': [-1, 26]}}, {'delay_ms': 81, 'motors': {}}, {'delay_ms': 83, 'motors': {}}, {'delay_ms': 85, 'motors': {'A': [-1, 25]}}, {'delay_ms': 81, 'motors': {}}, {'delay_ms': 82, 'motors': {}}, {'delay_ms': 83, 'motors': {}}, {'delay_ms': 83, 'motors': {'B': [1, 25]}}, {'delay_ms': 83, 'motors': {}}, {'delay_ms': 84, 'motors': {'B': [-1, 25]}}, {'delay_ms': 84, 'motors': {'A': [4, 101], 'B': [-1, 25]}}, {'delay_ms': 84, 'motors': {'A': [12, 305], 'B': [-9, 229]}}, {'delay_ms': 85, 'motors': {'A': [19, 478], 'B': [-12, 302]}}, {'delay_ms': 85, 'motors': {'A': [19, 478], 'B': [-21, 528]}}, {'delay_ms': 86, 'motors': {'A': [21, 522], 'B': [-24, 597]}}, {'delay_ms': 86, 'motors': {'A': [27, 671], 'B': [-22, 547]}}, {'delay_ms': 87, 'motors': {'A': [28, 688], 'B': [-12, 295]}}, {'delay_ms': 87, 'motors': {'A': [30, 737], 'B': [-6, 147]}}, {'delay_ms': 87, 'motors': {'A': [28, 688], 'B': [-6, 147]}}, {'delay_ms': 88, 'motors': {'A': [29, 705], 'B': [-7, 170]}}, {'delay_ms': 88, 'motors': {'A': [28, 680], 'B': [-5, 121]}}, {'delay_ms': 88, 'motors': {'A': [-333, 750], 'B': [-8, 194]}}, {'delay_ms': 88, 'motors': {'A': [26, 632], 'B': [-11, 267]}}, {'delay_ms': 88, 'motors': {'A': [21, 510], 'B': [-7, 170]}}, {'delay_ms': 91, 'motors': {'A': [17, 399], 'B': [-12, 282]}}, {'delay_ms': 89, 'motors': {'A': [5, 120], 'B': [-7, 168]}}, {'delay_ms': 90, 'motors': {}}, {'delay_ms': 90, 'motors': {}}, {'delay_ms': 621, 'motors': {}}, {'delay_ms': 91, 'motors': {}}, {'delay_ms': 91, 'motors': {}}, {'delay_ms': 91, 'motors': {}}, {'delay_ms': 92, 'motors': {}}, {'delay_ms': 92, 'motors': {}}, {'delay_ms': 92, 'motors': {}}]

async def main():
    print("FLL Timeline Replay")
    print(str(len(TIMELINE)) + " frames / 7424ms")

    for idx, frame in enumerate(TIMELINE):
        dt   = frame['delay_ms']
        cmds = frame['motors']

        # Fire all motors for this frame simultaneously (non-blocking)
        for port_name, cmd in cmds.items():
            if port_name in PORT_MAP:
                target_deg = cmd[0]
                speed      = cmd[1]
                if target_deg != 0:
                    motor.run_for_degrees(PORT_MAP[port_name], target_deg, speed)

        # Wait the exact recorded inter-frame interval
        # Motors started above keep running during this sleep -- correct behaviour,
        # as it mirrors how the robot moved during recording.
        if dt > 0:
            await runloop.sleep_ms(dt)

        if (idx + 1) % 20 == 0:
            print("frame " + str(idx + 1) + "/" + str(len(TIMELINE)))

    # Let any still-running motors finish
    await runloop.sleep_ms(300)
    print("Done!")

runloop.run(main())
