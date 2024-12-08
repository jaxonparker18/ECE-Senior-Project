# echo-server.py
import sys

sys.path.append('/usr/lib/python3/dist-packages')
import threading
from socket import *
import sys
import base64
import cv2
import time
import numpy as np
import imutils
import io
import struct
import math

# PI EXCLUSIVE
import serial
from gpiozero import Motor, Servo, PWMLED, LED, InputDevice, CPUTemperature
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from rpi_hardware_pwm import HardwarePWM
import PiBatteryIndicator


class UpdateServoThread(threading.Thread):
    """
    Controls the movement of the servos to support holding down a key.
    """

    def __init__(self, servo, pwm_val, pwm_max, pwm_min, direction):
        super().__init__()
        self.servo = servo
        self.direction = direction
        self.stop_event = threading.Event()
        self.current_pwm_val = pwm_val
        self.pwm_max = pwm_max
        self.pwm_min = pwm_min
        self.increment = 0.0003
        self.prev = round(servo._duty_cycle, 2)
        print(self.prev)

    def run(self):
        """
        Runs the thread which continuously moves the servo
        until thread is killed.
        """
        while not self.stop_event.is_set():
            if self.direction == UP:
                if self.current_pwm_val <= self.pwm_max:
                    self.current_pwm_val += self.increment
            elif self.direction == DOWN:
                if self.current_pwm_val >= self.pwm_min:
                    self.current_pwm_val -= self.increment
            elif self.direction == LEFT:
                if self.current_pwm_val <= self.pwm_max:
                    self.current_pwm_val += self.increment
            elif self.direction == RIGHT:
                if self.current_pwm_val >= self.pwm_min:
                    self.current_pwm_val -= self.increment
            self.servo.change_duty_cycle(self.current_pwm_val)
            rounded = round(self.current_pwm_val, 2)
            if self.prev != rounded:
                self.prev = rounded
                threading.Thread(target=self.notify_client, args=()).start()

    def stop(self):
        self.stop_event.set()

    def notify_client(self):
        if self.direction == UP or self.direction == DOWN:
            # print("/y" + str(round(self.current_pwm_val, 2)))
            send_to_client("/Y" + str(round(self.current_pwm_val, 2)))
        else:
            # print("/x" + str(round(self.current_pwm_val, 2)))
            send_to_client("/X" + str(round(self.current_pwm_val, 2)))


# CONSTS
UP = 0
DOWN = 1
LEFT = 2
RIGHT = 3
IDLE = 4

ON = "1"
OFF = "0"
DC = "x"

# NETWORK
encoder = 'utf-8'
sending_lock = threading.Lock()

FULL_SPEED = 0.75
TURN_SPEED = 0.10
W_TRACK_SPEED = 0.4
TRACK_SPEED = 0.125

A_SCAN_SPEED = 0.4

# UART - DEPRECIATED
# serial_port = '/dev/ttyAMA10'  # debug port -> '/dev/ttyAMA10', USB -> '/dev/USB0' | busted -> '/dev/ttyAMA0'
# baud_rate = 115200
# ser = serial.Serial(serial_port, baud_rate)

# GPIO MOTOR
left_motor = Motor("BOARD12", "BOARD13")  # 11 13
right_motor = Motor("BOARD18", "BOARD16")  # 18 16

# SERVOS
## MAX PWM IS 2.4MS or 12% DUTY CYCLE
## MIN PWM IS 0.8MS or  4% DUTY CYCLE
PWM_Y_MAX = 10
PWM_Y_MIN = 6.37
PWM_Y_MID = 7.5
pwm_y = HardwarePWM(pwm_channel=0, hz=50, chip=0)
current_pwm_y = PWM_Y_MID
pwm_y.start(current_pwm_y)
move_y_thread = None

PWM_X_MAX = 10.9
PWM_X_MIN = 8.1
PWM_X_MID = 10
pwm_x = HardwarePWM(pwm_channel=1, hz=50, chip=0)
current_pwm_x = PWM_X_MID
pwm_x.start(current_pwm_x)
move_x_thread = None

t = 0

# PUMP
pump = LED("BOARD15")
pump.off()

# WL SENSORS
wl_five = InputDevice("BOARD26")
wl_four = InputDevice("BOARD24")
wl_three = InputDevice("BOARD23")
wl_two = InputDevice("BOARD21")
wl_one = InputDevice("BOARD19")

# SERVER
client_socket = None

# control variables
w = DC
a = DC
s = DC
d = DC
space = DC
up = DC
down = DC
left = DC
right = DC
m_y = DC
m_x = DC
misc1 = DC
misc2 = DC

# threading
video_thread_SF = threading.Event()
commands_thread_SF = threading.Event()

pi_battery_thread_SF = threading.Event()
water_level_thread_SF = threading.Event()
cpu_temp_thread_SF = threading.Event()


def recv_data():
    """
    Receives the data coming in following the "prefixed with length protocol.
    :returns the data that was received
    """

    global client_socket
    raw_msg_len = client_socket.recv(4)  # get length of message

    if not raw_msg_len:
        return

    msg_len = struct.unpack("!I", raw_msg_len)[0]
    data = client_socket.recv(msg_len).decode(encoder)
    return data


def get_most_recent(data_bytes):
    """
    DEPRECIATED
    Gets the most recent command from data bytes.
    :param data_bytes: Bytes of data to be filtered
    :return: most recent bytes of data, 9 characters long
    """

    string_data = data_bytes.decode(encoder)
    return string_data


def send_to_client(message):
    """
    Sends the message using the "prefixed with length" protocol.
    :param message: message to be sent
    """
    with sending_lock:
        msg_len = len(message)
        client_socket.sendall(struct.pack("!I", msg_len))
        client_socket.sendall(message.encode(encoder))
        # print(message)


def set_motor(left_speed, right_speed):
    """
    Sets the left and right motor.
    :param left: value of left motor (0 - 1), where positive is forward and negative is backward
    :param right: value of right motor (0 - 1), where positive is forward and negative is backward
    """

    global left_motor
    global right_motor

    if left_speed == 0:
        left_motor.stop()
    elif left_speed > 0:
        left_motor.forward(left_speed)
    else:
        left_motor.backward(abs(left_speed))

    if right_speed == 0:
        right_motor.stop()
    elif right_speed > 0:
        right_motor.forward(right_speed)
    else:
        right_motor.backward(abs(right_speed))


def send_to_uart(bits):
    """
    DEPRECIATED
    Send bits to UART.
    :param bits: bits to be sent
    """

    for i in range(len(bits)):
        uart_command = str(bits[i]).encode('utf-8')
        ser.write(uart_command)


def execute_commands(bits):
    """
    Execute the commands based on bits, where bits is [w, a, s, d, space, up, down, left, right]
    :param bits: the values of each action
    """

    try:
        global w
        global a
        global s
        global d
        global space
        global up
        global down
        global left
        global right
        global m_y
        global m_x
        global misc1
        global misc2
        # FIRING MECHANISM
        global pwm_y
        global move_y_thread
        global pwm_x
        global move_x_thread

        bits = tuple(map(str, bits.split(",")))
        # print("bits are", bits)
        if bits[0] != DC:
            w = bits[0]
        if bits[1] != DC:
            a = bits[1]
        if bits[2] != DC:
            s = bits[2]
        if bits[3] != DC:
            d = bits[3]
        if bits[4] != DC:
            space = bits[4]
        if bits[5] != DC:
            up = bits[5]
        if bits[6] != DC:
            down = bits[6]
        if bits[7] != DC:
            left = bits[7]
        if bits[8] != DC:
            right = bits[8]
        if bits[9] != DC:
            m_y = bits[9]
        if bits[10] != DC:
            m_x = bits[10]
        if bits[11] != DC:
            misc1 = bits[11]
        if bits[12] != DC:
            misc2 = bits[12]
        # print("start", w, a, s, d, space, up, down, left, right, m_y, m_x, misc1, misc2)

        # MOVEMENT
        if w == ON and a == ON:
            set_motor(TURN_SPEED, FULL_SPEED)
            send_to_client("W and A executed.")
        elif w == ON and d == ON:
            set_motor(FULL_SPEED, TURN_SPEED)
            send_to_client("W and D executed.")
        elif w == ON and s == ON:
            set_motor(0, 0)
            send_to_client("W and S executed.")
        elif s == ON and a == ON:
            set_motor(-TURN_SPEED, -FULL_SPEED)
            send_to_client("S and A executed.")
        elif s == ON and d == ON:
            set_motor(-FULL_SPEED, -TURN_SPEED)
            send_to_client("S and D executed.")
        elif w == ON:
            if misc2 == 't':
                set_motor(W_TRACK_SPEED, W_TRACK_SPEED)
            else:
                set_motor(FULL_SPEED, FULL_SPEED)
            send_to_client("W executed.")
        elif s == ON:
            set_motor(-FULL_SPEED, -FULL_SPEED)
            send_to_client("S executed.")
        elif a == ON:
            if misc2 == 't':
                set_motor(-float(misc1), float(misc1))
            elif misc2 == 's':
                set_motor(-A_SCAN_SPEED, A_SCAN_SPEED)
            else:
                set_motor(-FULL_SPEED, FULL_SPEED)
            send_to_client("A executed.")
        elif d == ON:
            if misc2 == 't':
                set_motor(float(misc1), -float(misc1))
            else:
                set_motor(FULL_SPEED, -FULL_SPEED)
            send_to_client("D executed.")
        else:
            set_motor(0, 0)
            # send_to_client("Movement IDLE")

        # DC case: both up and down keys are pressed
        # KEYBOARD CONTROL

        if misc1 == 'm':
            pwm_y.change_duty_cycle(float(m_y))
            send_to_client("/Y" + str(round(float(m_y), 2)))
        else:
            if up == ON and move_y_thread is None:
                move_y_thread = UpdateServoThread(pwm_y, pwm_y._duty_cycle, PWM_Y_MAX, PWM_Y_MIN, UP)
                move_y_thread.start()

            elif up == OFF:
                if move_y_thread is not None and move_y_thread.is_alive():
                    move_y_thread.stop()
                    move_y_thread.join()
                    move_y_thread = None

            elif down == ON and move_y_thread is None:
                move_y_thread = UpdateServoThread(pwm_y, pwm_y._duty_cycle, PWM_Y_MAX, PWM_Y_MIN, DOWN)
                move_y_thread.start()

            elif down == OFF:
                if move_y_thread is not None and move_y_thread.is_alive():
                    move_y_thread.stop()
                    move_y_thread.join()
                    move_y_thread = None

        if misc1 == 'm':
            pwm_x.change_duty_cycle(float(m_x))
            send_to_client("/X" + str(round(float(m_x), 2)))
        else:
            if left == ON and move_x_thread is None:
                move_x_thread = UpdateServoThread(pwm_x, pwm_x._duty_cycle, PWM_X_MAX, PWM_X_MIN, LEFT)
                move_x_thread.start()

            elif left == OFF:
                if move_x_thread is not None and move_x_thread.is_alive():
                    move_x_thread.stop()
                    move_x_thread.join()
                    move_x_thread = None

            elif right == ON and move_x_thread is None:
                move_x_thread = UpdateServoThread(pwm_x, pwm_x._duty_cycle, PWM_X_MAX, PWM_X_MIN, RIGHT)
                move_x_thread.start()

            elif right == OFF:
                if move_x_thread is not None and move_x_thread.is_alive():
                    move_x_thread.stop()
                    move_x_thread.join()
                    move_x_thread = None

        if space == ON:
            pump.on()
            # send_to_client("Spraying")

        if space == OFF:
            pump.off()
            # send_to_client("Stop spraying...")

        # send_to_client("/NP" +  + "," + )

        # reset if 0
        if bits[0] == OFF:
            w = DC
        if bits[1] == OFF:
            a = DC
        if bits[2] == OFF:
            s = DC
        if bits[3] == OFF:
            d = DC
        if bits[4] == OFF:
            space = DC
        if bits[5] == OFF:
            up = DC
        if bits[6] == OFF:
            down = DC
        if bits[7] == OFF:
            left = DC
        if bits[8] == OFF:
            right = DC
        if bits[9] == OFF:
            m_y = DC
        if bits[10] == OFF:
            m_x = DC
        if bits[11] == OFF:
            misc1 = DC
        if bits[12] == OFF:
            misc2 = DC
        # print("end", w, a, s, d, space, up, down, left, right, m_y, m_x, misc1, misc2)

    except Exception as e:
        send_to_client("ERROR OCCURED: " + repr(e))


def circle_motion():
    global pwm_x, pwm_y
    global t
    radius = 1
    speed = 0.01
    multiplier = 0.7
    while True:
        # Calculate x(t) and y(t) for circular motion
        x = radius * math.cos(t)
        y = radius * math.sin(t)

        # Map the x and y values to PWM duty cycles
        # Assuming the range of motion is between min_pwm and max_pwm
        px = PWM_X_MIN + ((x * multiplier / radius) + 1) * (PWM_X_MAX - PWM_X_MIN) / 2  # Map x to PWM range
        py = PWM_Y_MIN + ((y * multiplier / radius) + 1) * (PWM_Y_MAX - PWM_Y_MIN) / 2  # Map y to PWM range

        # print(px)
        # print(py)
        pwm_x.change_duty_cycle(px)
        pwm_y.change_duty_cycle(py)

        # Move to the next step (increase t to simulate motion)
        t += 0.1 * speed  # Adjust speed by changing this value

        # Loop back to 0 when t completes a full circle (2*pi radians)
        if t >= 2 * math.pi:
            t = 0
        # time.sleep(0.1)


def update_pi_battery(pi_battery):
    while not pi_battery_thread_SF.is_set():
        send_to_client("/PIB" + str(pi_battery.getPercentage()))
        time.sleep(5)


def update_water_level():
    while not water_level_thread_SF.is_set():
        level = ["0", "0", "0", "0", "0"]
        if not wl_five.is_active:
            level[4] = "1"
        if not wl_four.is_active:
            level[3] = "1"
        if not wl_three.is_active:
            level[2] = "1"
        if not wl_two.is_active:
            level[1] = "1"
        if not wl_one.is_active:
            level[0] = "1"
        send_to_client("/WL" + "".join(level))
        time.sleep(2)


def update_cpu_temp():
    cpu_temp = CPUTemperature(min_temp=50, max_temp=90)
    while not cpu_temp_thread_SF.is_set():
        send_to_client("/CT" + str(round(cpu_temp.temperature, 1)))
        time.sleep(5)


def update_servo_max_min():
    global PWM_X_MAX, PWM_X_MIN, PWM_Y_MAX, PWM_Y_MIN
    send_to_client("/MM" + str(PWM_X_MAX) + "," + str(PWM_X_MIN) +
                   "," + str(PWM_Y_MAX) + "," + str(PWM_Y_MIN))


def handle_commands():
    """
    Establishes handshake with TCP Client and listens to any commands sent from the client.
    """

    global client_socket
    while not commands_thread_SF.is_set():
        try:
            client_socket, tcp_address = commands_socket.accept()
            print(f"Command center connected at {tcp_address}.")
            send_to_client("Connection established.")
            # start pi_battery thread
            pi_battery = PiBatteryIndicator.INA219(addr=0x41)
            pi_battery_thread = threading.Thread(target=update_pi_battery, args=(pi_battery,), daemon=True)
            pi_battery_thread_SF.clear()
            pi_battery_thread.start()

            # start water_level thread
            water_level_thread = threading.Thread(target=update_water_level, args=(), daemon=True)
            water_level_thread_SF.clear()
            water_level_thread.start()

            # start cpu_temp thread
            cpu_temp_thread = threading.Thread(target=update_cpu_temp, args=(), daemon=True)
            cpu_temp_thread_SF.clear()
            cpu_temp_thread.start()

            update_servo_max_min()

            # threading.Thread(target=circle_motion).start()

            while True:
                try:
                    # data = client_socket.recv(1024) # , MSG_WAITALL
                    data = recv_data()
                    if data:
                        print("data is " + data)
                        execute_commands(data)
                    if not data:
                        print("Commands disconnected from control center: No data")
                        break
                except KeyboardInterrupt:
                    print("Commands disconnected from control center: Keyboard Interrupt exception")
                    client_socket.close()
                    pi_battery_thread_SF.set()
                    pi_battery_thread.join()
                    water_level_thread_SF.set()
                    water_level_thread.join()
                    cpu_temp_thread_SF.set()
                    cpu_temp_thread.join()
                    commands_thread_SF.set()
                    # sys.exit(0)
                # except:
                #    print("Commands disconnected from control center: Failed to receive exception")
                #    clean_up()
                #    break
        except KeyboardInterrupt:
            print("Server hard-stopped with CTRL + C.")
            client_socket.close()
            pi_battery_thread_SF.set()
            pi_battery_thread.join()
            water_level_thread_SF.set()
            water_level_thread.join()
            cpu_temp_thread_SF.set()
            cpu_temp_thread.join()

            commands_thread_SF.set()
            # sys.exit(0)


def handle_video():
    """
    Starts the PiCamera and sends video feed from the camera to TCP client.
    """

    picam2 = Picamera2()
    # (3280, 2646), (1920, 1080), (1640, 1232), (640, 480)
    picam2.configure(picam2.create_preview_configuration(
        main={"format": 'XRGB8888', "size": (1640, 1232)}))  # "libcamera-hello -t 1 --nopreview" for all resolutions
    picam2.start()

    while not video_thread_SF.is_set():
        client_sock, tcp_address = video_socket.accept()
        print(f"Video control connected at {tcp_address}.")
        while True:
            im = picam2.capture_array()
            encoded, buffer = cv2.imencode('.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 70])
            message = base64.b64encode(buffer) + b'\0'
            try:
                client_sock.sendto(message, tcp_address)
            except KeyboardInterrupt:
                print("Server hard-stopped with CTRL + C.")
                client_sock.close()
                video_thread_SF.set()
                sys.exit(0)
            except:
                video_thread_SF.set()
                video_thread.join()
                print("Video control disconnected from control center")
                break


BUFF_SIZE = 65536

HOST = "10.42.0.1"  # Standard loopback interface address (localhost)

# COMMANDS SOCKET
commands_port = 2100  # Port to listen on (non-privileged ports are > 1023)
commands_socket = socket(AF_INET, SOCK_STREAM)
commands_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
commands_socket.bind((HOST, commands_port))
commands_socket.listen(1)

# VIDEO SOCKET
video_port = 2101  # Port to listen on (non-privileged ports are > 1023)
video_socket = socket(AF_INET, SOCK_STREAM)
video_socket.setsockopt(SOL_SOCKET, SO_RCVBUF, BUFF_SIZE)
video_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
video_socket.bind((HOST, video_port))
video_socket.listen(1)

commands_thread = threading.Thread(target=handle_commands, args=())
commands_thread_SF.clear()
commands_thread.start()

video_thread = threading.Thread(target=handle_video, args=())
video_thread_SF.clear()
video_thread.start()

print("Server online...")

commands_thread.join()
video_thread.join()
