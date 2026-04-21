# Run on Lego Spike

"""
Legend:
A: Motor
B: Motor
C: Bottom Motor (Gyro)
D: Distance Sensor
E: Force Sensor
F: Force Sensor
"""

import motor
import force_sensor
import distance_sensor
import time
import runloop
from hub import port, motion_sensor, button, light_matrix

recording = False

async def check_buttons():
    global recording

    while True:
        if button.pressed(button.LEFT) > 0:
            recording = True
            light_matrix.show_image(light_matrix.IMAGE_YES)

            # csv header
            print(
                "time_ms,"
                "motorA_rel_deg,motorA_abs_deg,"
                "motorB_rel_deg,motorB_abs_deg,"
                "force_N,"
                "distance_mm,"
                "yaw_deg,pitch_deg,roll_deg\r\n",
                end=""
            )

            motor.reset_relative_position(port.A, 0)
            motor.reset_relative_position(port.B, 0)
            #motor.reset_relative_position(port.C, 0)

            while button.pressed(button.LEFT) > 0:
                await runloop.sleep_ms(10)

        if button.pressed(button.RIGHT) > 0:
            recording = False
            light_matrix.show_image(light_matrix.IMAGE_NO)
            print("#recording_stopped\r\n", end="")

            while button.pressed(button.RIGHT) > 0:
                await runloop.sleep_ms(10)

        await runloop.sleep_ms(10)


async def collect_data():
    global recording
    start_time = time.ticks_ms()
    sample_interval = 150  # ms

    while True:
        if recording:
            t = time.ticks_ms() - start_time

            a_rel = motor.relative_position(port.A)
            b_rel = motor.relative_position(port.B)

            a_abs = motor.absolute_position(port.A)
            b_abs = motor.absolute_position(port.B)

            yaw, pitch, roll = motion_sensor.tilt_angles()
            yaw /= 10
            pitch /= 10
            roll /= 10

            # force sensor
            force = force_sensor.force(port.F)

            # distance sensor
            dist = distance_sensor.distance(port.D)

            # copy pastable csv
            print(
                str(t) + "," +
                str(a_rel) + "," + str(a_abs) + "," +
                str(b_rel) + "," + str(b_abs) + "," +
                str(force) + "," +
                str(dist) + "," +
                str(yaw) + "," + str(pitch) + "," + str(roll)
            )

            await runloop.sleep_ms(sample_interval)

        else:
            start_time = time.ticks_ms()
            await runloop.sleep_ms(100)


light_matrix.write("Ready")
print("#FLL Robot Data Logger\r\n", end="")

runloop.run(check_buttons(), collect_data())