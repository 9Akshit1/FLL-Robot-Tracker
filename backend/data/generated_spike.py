import runloop
import motor
from hub import port

timeline = [(188, 0, -1, 0), (188, 0, 0, 0), (189, -2, 2, 0), (189, -2, 1, 0), (192, 0, 7, 0), (189, 0, 1, 0), (190, 0, 0, 0), (190, -1, 10, 0), (190, 0, 43, 0), (191, 0, 38, 0), (192, 0, 30, 0), (194, -19, 27, 0), (191, -57, 49, 0), (192, -43, 40, 0), (193, -8, 4, 0), (723, 10, -8, 0), (193, 0, 4, 0), (194, -3, 3, -1), (193, -3, 1, -7), (195, -1, -2, -51), (193, -1, 1, -38), (195, 0, 0, -37), (195, 0, 0, -32), (196, 0, 0, -17), (196, 0, 1, -1), (196, 0, -1, 3), (197, 0, 0, 3), (197, 0, 0, 3), (197, 0, 0, 17), (197, 0, 0, 36), (198, 1, 0, 29), (198, 1, 0, 29), (198, 0, 0, 2), (199, -2, 0, 1), (199, 5, -6, 0), (201, 0, 1, -1), (199, -1, -5, 0), (201, 7, -12, 1), (200, 64, -49, -1), (201, 68, -65, 0), (201, 70, -73, 0), (203, 62, -69, 0), (201, 45, -46, 0), (204, 1, -2, 0), (202, -2, 3, 1), (204, -1, -1, -1), (204, 0, 1, 0)]

def compute_speed(deg, dt):
    if dt <= 0:
        return 0
    speed = int((abs(deg) / dt) * 1000)
    return max(100, min(speed, 1000))

async def move_motors(dt, dA, dB, dC):
    if dA != 0:
        motor.run_for_degrees(port.A, dA, compute_speed(dA, dt))
    if dB != 0:
        motor.run_for_degrees(port.B, dB, compute_speed(dB, dt))
    if dC != 0:
        motor.run_for_degrees(port.C, dC, compute_speed(dC, dt))
    if dt > 0:
        await runloop.sleep_ms(dt)

async def main():
    for motion in timeline:
        await move_motors(*motion)
    print("Replay complete")

runloop.run(main())
