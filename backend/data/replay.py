import runloop
import motor
from hub import port


# Motor setup
left_motor = port.A
right_motor = port.B

# Helper function to calculate motor speed
def get_speed(degrees, time_ms):
    if time_ms <= 0 or degrees == 0:
        return 0
    speed = int((abs(degrees) / time_ms) * 1000)
    return max(100, min(1000, speed))

# Semantic movement functions
def move_forward(distance_deg, speed=500):
    '''Drive robot forward'''
    motor.run_for_degrees(left_motor, distance_deg, speed)
    motor.run_for_degrees(right_motor, distance_deg, speed)

def move_backward(distance_deg, speed=500):
    '''Drive robot backward'''
    motor.run_for_degrees(left_motor, -distance_deg, speed)
    motor.run_for_degrees(right_motor, -distance_deg, speed)

def turn_left(angle_deg, speed=400):
    '''Turn robot left in place'''
    motor.run_for_degrees(left_motor, -angle_deg, speed)
    motor.run_for_degrees(right_motor, angle_deg, speed)

def turn_right(angle_deg, speed=400):
    '''Turn robot right in place'''
    motor.run_for_degrees(left_motor, angle_deg, speed)
    motor.run_for_degrees(right_motor, -angle_deg, speed)

def move_custom(left_deg, right_deg, speed=500):
    '''Move with different speeds on each side (for curves)'''
    motor.run_for_degrees(left_motor, left_deg, speed)
    motor.run_for_degrees(right_motor, right_deg, speed)


async def main():
    '''Main replay routine'''
    print("Starting replay...")
    
    # Execute recorded movements
    move_custom(0, 1, 100)
    move_custom(0, 2, 100)
    move_custom(0, -1, 100)
    move_custom(1, -2, 100)
    turn_left(5, 100)
    turn_left(22, 126)
    turn_left(32, 176)
    turn_left(33, 181)
    turn_left(32, 168)
    turn_left(30, 155)
    turn_left(32, 170)
    turn_left(29, 163)
    turn_left(31, 166)
    turn_left(28, 146)
    turn_left(24, 131)
    turn_left(20, 110)
    turn_left(19, 100)
    turn_left(22, 119)
    turn_left(5, 100)
    
    print("Done!")

# Run the program
runloop.run(main())
