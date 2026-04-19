import runloop
import motor
from hub import port

timeline = [(234, 1, 0, -1), (187, 0, 0, 0), (187, 0, 0, 0), (188, 0, 0, 0), (188, 0, 0, 0), (188, 0, 0, 1), (189, 1, -1, -1), (189, -1, -6, 1), (190, 2, 2, 0), (189, -11, 7, 0), (191, -2, 0, -1), (189, -56, 0, 1), (191, -43, 0, 0), (190, -43, 0, 0), (191, -49, 0, 0), (191, -35, 0, 0), (676, -66, -1, 0), (192, -19, 0, 0), (192, -10, 0, 0), (192, 10, 0, -1), (192, 58, 0, 0), (193, 68, 0, 1), (194, 58, -4, -1), (194, 57, -3, 0), (195, 42, 0, 0), (194, 27, 7, 1), (194, 4, -9, 0), (192, -1, 0, 0)]

def compute_speed(deg, dt):
    if dt <= 0:
        return 0
    speed = int((abs(deg) / dt) * 1000)
    return max(100, min(speed, 1000))

async def move_motors(dt, da, db, dc):
    if da != 0:
        motor.run_for_degrees(port.A, da, compute_speed(da, dt))
    if db != 0:
        motor.run_for_degrees(port.B, db, compute_speed(db, dt))
    if dc != 0:
        motor.run_for_degrees(port.C, dc, compute_speed(dc, dt))
    if dt > 0:
        await runloop.sleep_ms(dt)

async def main():
    for motion in timeline:
        await move_motors(*motion)
    print("Replay complete")

runloop.run(main())
