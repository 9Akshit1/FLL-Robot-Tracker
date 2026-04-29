import runloop
import motor
from hub import port

timeline = [(186, 0, 1, 0), (188, 0, 0, 0), (187, 0, 0, 0), (188, 0, 0, 0), (186, 0, 0, 0), (189, 0, 0, 0), (188, 3, -3, 0), (188, 0, 0, 0), (189, 0, 0, 0), (188, 0, 0, 0), (190, 0, 0, 0), (190, 1, 0, 0), (190, 0, -1, 0)]

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
