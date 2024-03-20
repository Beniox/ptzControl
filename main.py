import pygame
import requests
import math
import cv2
from datetime import datetime
import XInput
import time
from pyeasyremote import EasyRemote

# Threshold for joystick movement
AXIS_THRESHOLD = 0.2

# IP address of the camera
ip = "192.168.5.163"

# EasyRemote object, to control the lights
er = EasyRemote("172.19.19.221")


# URL for the fetch request
URL = f"http://{ip}/ajaxcom"
rtsp_url = f"rtsp://{ip}:554/live/av0"

# Headers for the fetch request
HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-US,en;q=0.9,de;q=0.8",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-requested-with": "XMLHttpRequest"
}


# Function to vibrate the Xbox controller
def vibrate_xbox_controller(sec):
    controller = XInput.get_connected()
    if controller:
        XInput.set_vibration(0, 65535, 65535)
        time.sleep(sec)
        XInput.set_vibration(0, 0, 0)


# Function to send fetch request
def send_fetch_request(data):
    response = requests.post(URL, headers=HEADERS, data=data)
    print(response.text)


# Function to generate data with speed
def generate_data(cmd, speed=50):
    return {
        "szCmd": f'{{"SysCtrl":{{"PtzCtrl":{{"nChanel":0,"szPtzCmd":"{cmd}","byValue":{speed}}}}}}}'
    }


def move(direction, speed=50):
    send_fetch_request(generate_data(direction, speed))


def capture_rtsp_screenshot(url):
    # Open RTSP stream
    cap = cv2.VideoCapture(url)

    # Check if the capture was successful
    if not cap.isOpened():
        print("Error: Unable to open RTSP stream")
        return

    # Read a frame from the stream
    ret, frame = cap.read()

    # Check if frame reading was successful
    if not ret:
        print("Error: Unable to read frame from RTSP stream")
        return

    # Generate timestamp for the filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"images/screenshot_{timestamp}.jpg"

    # Write the frame to an image file
    cv2.imwrite(output_file, frame)

    # Release the capture
    cap.release()

    print("Screenshot saved as", output_file)


def main():
    global x_axis, y_axis, z_axis

    pygame.init()
    pygame.joystick.init()

    # Check if any joysticks/controllers are connected
    if pygame.joystick.get_count() == 0:
        print("No joysticks/controllers found.")
        return

    # Initialize the first joystick/controller
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    print("Joystick initialized: {}".format(joystick.get_name()))

    movement = ""
    zoom = ""
    curspeed = 50
    lightstate = False
    speed = 50
    try:
        # Main loop
        while True:
            try:
                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.JOYDEVICEREMOVED:
                        print("Joystick removed")
                        joystick.quit()

                    elif event.type == pygame.JOYDEVICEADDED:
                        print("Joystick added")
                        joystick.init()

                    if event.type == pygame.QUIT:
                        return
                    # left shoulder button
                    elif event.type == pygame.JOYBUTTONDOWN:
                        if event.button == 4:
                            print("Left shoulder button pressed")
                            move("preset_set", 254)
                        if event.button == 5:
                            print("Right shoulder button pressed")
                            move("preset_call", 254)

                        if event.button == 3:
                            vibrate_xbox_controller(0.15)
                            capture_rtsp_screenshot(rtsp_url)

                        if event.button == 0:
                            print("Button A pressed")
                            lightstate = not lightstate
                            er.objects["black"].set_state(lightstate)

                    elif event.type == pygame.JOYAXISMOTION:
                        # Handle joystick axis motion
                        x_axis = joystick.get_axis(0)
                        y_axis = joystick.get_axis(1)
                        z_axis = joystick.get_axis(3)

                        r_trigger = joystick.get_axis(5)

                        if r_trigger > -0.99:
                            speed = int((r_trigger + 1) * 100)

                        else:
                            speed = 50

                        # Calculate angle of joystick movement
                        angle = math.atan2(y_axis, x_axis)
                        angle_degrees = math.degrees(angle) % 360

                        # Determine direction based on angle
                        new_zoom = ""
                        new_movement = ""
                        if abs(x_axis) > AXIS_THRESHOLD or abs(y_axis) > AXIS_THRESHOLD:
                            if 22.5 <= angle_degrees < 67.5:
                                new_movement = "rightdown"
                            elif 67.5 <= angle_degrees < 112.5:
                                new_movement = "down"
                            elif 112.5 <= angle_degrees < 157.5:
                                new_movement = "leftdown"
                            elif 157.5 <= angle_degrees < 202.5:
                                new_movement = "left"
                            elif 202.5 <= angle_degrees < 247.5:
                                new_movement = "leftup"
                            elif 247.5 <= angle_degrees < 292.5:
                                new_movement = "up"
                            elif 292.5 <= angle_degrees < 337.5:
                                new_movement = "rightup"
                            elif angle_degrees >= 337.5 or angle_degrees < 22.5:
                                new_movement = "right"

                        if abs(z_axis) > AXIS_THRESHOLD:
                            if z_axis < 0:
                                new_zoom = "zoomadd"

                            else:
                                new_zoom = "zoomdec"
                        else:
                            new_zoom = "stop"

                        if new_zoom != zoom:
                            if new_zoom == "stop":
                                cmd = f'{zoom}_stop'
                                move(cmd)
                            if new_zoom != "stop":
                                cmd = f'{new_zoom}_start'
                                move(cmd)
                            zoom = new_zoom

                        # Send start command for new movement with calculated speed
                        if new_movement != movement or curspeed != speed:
                            if movement != "":
                                # Send stop command for previous movement
                                cmd = f'{movement}_stop'
                                curspeed = speed
                                move(cmd, speed)

                            # Send start command for new movement
                            if new_movement != "":
                                cmd = f'{new_movement}_start'
                                move(cmd, speed)

                            movement = new_movement

                # If joystick is at rest, send stop command
                if movement != "" and (abs(x_axis) <= AXIS_THRESHOLD and abs(y_axis) <= AXIS_THRESHOLD):
                    cmd = f'{movement}_stop'
                    move(cmd)
                    movement = ""

            except Exception as e:
                print(e)
                time.sleep(1)
                print("restarting")

    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main()
