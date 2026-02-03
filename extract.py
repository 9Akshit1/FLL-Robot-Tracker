# RUN FROM THE SPIKE LEGOEDUCATION WEBSITE

import csv
import motor
import time
import runloop
from hub import port, motion_sensor, button, light_matrix

recording = False
data_points = []

async def check_buttons():
    """Monitor buttons to start/stop recording"""
    global recording

    while True:
        # Left button starts recording
        if button.pressed(button.LEFT) > 0:
            recording = True
            light_matrix.show_image(light_matrix.IMAGE_YES)
            print("=== Recording Started ===")
            print("Time(ms), MotorA_Relative, MotorA_Absolute, MotorB_Relative, MotorB_Absolute, Yaw, Pitch, Roll")

            # Reset relative positions to 0 at start
            motor.reset_relative_position(port.A, 0)
            motor.reset_relative_position(port.B, 0)

            # Wait for button release
            while button.pressed(button.LEFT) > 0:
                await runloop.sleep_ms(10)

        # Right button stops recording
        if button.pressed(button.RIGHT) > 0:
            recording = False
            light_matrix.show_image(light_matrix.IMAGE_NO)
            print("=== Recording Stopped ===")
            print("Total data points collected:", len(data_points))

            # Wait for button release
            while button.pressed(button.RIGHT) > 0:
                await runloop.sleep_ms(10)

        await runloop.sleep_ms(10)

async def collect_data():
    """Collect sensor data when recording is active"""
    global recording, data_points
    start_time = time.ticks_ms()
    sample_interval = 50# Sample every 50ms for smooth data

    while True:
        if recording:
            # Get current time relative to start
            current_time = time.ticks_ms() - start_time

            # Get RELATIVE motor positions (from start of recording)
            motor_a_relative = motor.relative_position(port.A)
            motor_b_relative = motor.relative_position(port.B)

            # Get ABSOLUTE motor positions (true physical angle)
            motor_a_absolute = motor.absolute_position(port.A)
            motor_b_absolute = motor.absolute_position(port.B)

            # Get gyroscope data (yaw, pitch, roll in decidegrees)
            # Decidegrees = 1/10 of a degree
            yaw, pitch, roll = motion_sensor.tilt_angles()

            # Convert decidegrees to degrees for easier reading
            yaw_deg = yaw / 10.0
            pitch_deg = pitch / 10.0
            roll_deg = roll / 10.0

            # Store data point
            data_point = (current_time, motor_a_relative, motor_a_absolute,
                        motor_b_relative, motor_b_absolute,
                        yaw_deg, pitch_deg, roll_deg)
            data_points.append(data_point)

            # Print data in CSV format
            print(current_time, motor_a_relative, motor_a_absolute, motor_b_relative, motor_b_absolute, yaw_deg, pitch_deg, roll_deg)

            # Wait for next sample
            await runloop.sleep_ms(sample_interval)
        else:
            # Reset start time and data when not recording
            start_time = time.ticks_ms()
            if not recording and len(data_points) > 0:
                data_points = []
            await runloop.sleep_ms(100)

def save_to_csv(data, filename="output.csv"):
    """Saves collected data points to a csv file."""
    # Define headers based on your data structure
    headers = ["Time(ms)", "motor_a_relative", "motor_a_absolute", "Motor_b_relative","motor_b_abs", "yaw_deg", "pitch_deg", "roll_deg"]

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # The header row
        writer.writerow(headers)

        # Write all data rows at once
        writer.writerows(data)
    print(f"Successfully saved {len(data)} rows to {filename}")

# Show ready message
light_matrix.write("Ready!")
print("=== FLL Robot Data Logger ===")
print("Press LEFT button to START recording")
print("Press RIGHT button to STOP recording")
print("")
print("Motor positions are in DEGREES:")
print("- Relative: Degrees moved since recording started (resets to 0)")
print("- Absolute: True physical angle of motor shaft (never resets)")
print("")

# Run both coroutines
runloop.run(check_buttons(), collect_data())

# Save data to CSV when program ends
save_to_csv(data_points)
