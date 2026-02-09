# NOTE: RUN FROM THE SPIKE LEGO EDUCATION WEBSITE (or VS Code → run on hub)

import motor
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

            # CSV header (NO SPACES)
            print(
                "time_ms,"
                "motorA_rel_deg,motorA_abs_deg,"
                "motorB_rel_deg,motorB_abs_deg,"
                "motorC_rel_deg,motorC_abs_deg,"
                "yaw_deg,pitch_deg,roll_deg\r\n",
                end=""
            )

            motor.reset_relative_position(port.A, 0)
            motor.reset_relative_position(port.B, 0)
            motor.reset_relative_position(port.C, 0)

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
            c_rel = motor.relative_position(port.C)
            #c_rel = 0

            a_abs = motor.absolute_position(port.A)
            b_abs = motor.absolute_position(port.B)
            c_abs = motor.absolute_position(port.C)
            #c_abs = 0

            yaw, pitch, roll = motion_sensor.tilt_angles()
            yaw /= 10
            pitch /= 10
            roll /= 10

            # Copy pasteable csv format. FLL python doesnt allow to use proper import csv library stuff
            print(
                str(t) + "," +
                str(a_rel) + "," + str(a_abs) + "," +
                str(b_rel) + "," + str(b_abs) + "," +
                str(c_rel) + "," + str(c_abs) + "," +
                str(yaw) + "," + str(pitch) + "," + str(roll)
            )

            await runloop.sleep_ms(sample_interval)

        else:
            start_time = time.ticks_ms()
            await runloop.sleep_ms(100)


light_matrix.write("Ready")
print("#FLL Robot Data Logger\r\n", end="")

runloop.run(check_buttons(), collect_data())