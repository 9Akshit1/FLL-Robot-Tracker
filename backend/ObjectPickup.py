from hub import port, light_matrix
import runloop
import motor
import motor_pair
import distance_sensor

motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)

DRIVE_SPEED = 250
BACK_SPEED = -150
BACK_TIME_MS = 2000

CLAW_HOME = 0
CLAW_LIFT = -100

TRIGGER_DISTANCE = 50

async def main():
    await light_matrix.write("INIT")

    await motor.run_to_relative_position(port.C, CLAW_HOME, 200)
    await runloop.sleep_ms(300)

    motor.reset_relative_position(port.C, 0)

    await light_matrix.write("GO")

    motor_pair.move(motor_pair.PAIR_1, 0, velocity=DRIVE_SPEED)

    last_dist = 9999

    while True:
        dist = distance_sensor.distance(port.D)

        if dist is None:
            dist = last_dist
        else:
            last_dist = dist

        if dist > 1000 and last_dist < 200:
            dist = last_dist

        if dist > 0 and dist <= TRIGGER_DISTANCE:
            break

        await runloop.sleep_ms(10)

    motor_pair.stop(motor_pair.PAIR_1)

    await light_matrix.write("GRAB")

    motor_pair.move(motor_pair.PAIR_1, 0, velocity=BACK_SPEED)

    motor.run_to_relative_position(port.C, CLAW_HOME + CLAW_LIFT, 80)

    await runloop.sleep_ms(BACK_TIME_MS)

    motor_pair.stop(motor_pair.PAIR_1)

    await light_matrix.write("DONE")

runloop.run(main())