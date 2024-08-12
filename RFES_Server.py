# echo-server.py
# LAST UPDATE: Nathan - 8/12/2024 - 12:12PM
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
# PI EXCLUSIVE
import serial
from gpiozero import Motor, Servo, PWMLED, LED
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from rpi_hardware_pwm import HardwarePWM


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
        self.increment = 0.0001

    def run(self):
        global PWM_MIN
        global PWM_MAX
        while not self.stop_event.is_set():
            if self.direction == UP:
                if self.current_pwm_val >= self.pwm_min:
                    self.current_pwm_val -= self.increment
            elif self.direction == DOWN:
                if self.current_pwm_val <= self.pwm_max:
                    self.current_pwm_val += self.increment
            self.servo.change_duty_cycle(self.current_pwm_val)

    def stop(self):
        self.stop_event.set()


# CONSTS
UP = 0
DOWN = 1
LEFT = 2
RIGHT = 3
IDLE = 4

ON = "1"
OFF = "0"
DC = "x"

# UART - DEPRECIATED
serial_port = '/dev/ttyAMA10'  # debug port -> '/dev/ttyAMA10', USB -> '/dev/USB0' | busted -> '/dev/ttyAMA0'
baud_rate = 115200
ser = serial.Serial(serial_port, baud_rate)

# GPIO MOTOR
left_motor = Motor("BOARD11", "BOARD13")
right_motor = Motor("BOARD18", "BOARD16")

# SERVOS
## MAX PWM IS 2.4MS or 12% DUTY CYCLE
## MIN PWM IS 0.8MS or  4% DUTY CYCLE
PWM_MAX = 10
PWM_MIN = 6
PWM_MID = 8
pwm_y = HardwarePWM(pwm_channel=2, hz=50, chip=2)
current_pwm_y = PWM_MID
pwm_y.start(current_pwm_y)

move_y_thread = None

# PUMP
pump = LED("BOARD15")
pump.off()

# SERVER
client_socket = None


def get_most_recent(data_bytes):
    """
    Gets the most recent command from data bytes.
    :param data_bytes: Bytes of data to be filtered
    :return: most recent bytes of data, 9 characters long
    """
    string_data = data_bytes.decode('utf-8')
    return string_data[len(string_data) - 9: len(string_data)]


def send_to_client(data):
    print("sent")
    client_socket.sendall((''.join(data).encode('utf-8')))


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
    # print("sent to UART: " + bits)


def execute_commands(bits):
    """
    Execute the commands based on bits, where bits is [w, a, s, d, space, up, down, left, right]
    :param bits: 9 characters long
    """
    try:
        print(bits)
        if len(bits) != 9:
            return

        w, a, s, d, space, up, down, left, right = bits
        # MOVEMENT
        if w == ON and a == ON:
            set_motor(0.10, 0.75)
            send_to_client("W and A executed.")
        elif w == ON and d == ON:
            set_motor(0.75, 0.10)
            send_to_client("W and D executed.")
        elif w == ON and s == ON:
            set_motor(0, 0)
            send_to_client("W and S executed.")
        elif s == ON and a == ON:
            set_motor(-0.25, -0.75)
            send_to_client("S and A executed.")
        elif s == ON and d == ON:
            set_motor(-0.75, -0.25)
            send_to_client("S and D executed.")
        elif w == ON:
            set_motor(0.75, 0.75)
            send_to_client("W executed.")
        elif s == ON:
            set_motor(-0.75, -0.75)
            send_to_client("S executed.")
        elif a == ON:
            set_motor(-0.75, 0.75)
            send_to_client("A executed.")
        elif d == ON:
            set_motor(0.75, -0.75)
            send_to_client("D executed.")
        else:
            set_motor(0, 0)
            send_to_client("Movement IDLE")

        # FIRING MECHANISM
        global pwm_y
        global move_y_thread

        # DC case: both up and down keys are pressed

        if up == ON and move_y_thread is None:
            move_y_thread = UpdateServoThread(pwm_y, pwm_y._duty_cycle, PWM_MAX, PWM_MIN, UP)
            move_y_thread.start()

        elif up == OFF:
            if move_y_thread is not None and move_y_thread.is_alive():
                move_y_thread.stop()
                move_y_thread.join()
                move_y_thread = None

        elif down == ON and move_y_thread is None:
            move_y_thread = UpdateServoThread(pwm_y, pwm_y._duty_cycle, PWM_MAX, PWM_MIN, DOWN)
            move_y_thread.start()

        elif down == OFF:
            if move_y_thread is not None and move_y_thread.is_alive():
                move_y_thread.stop()
                move_y_thread.join()
                move_y_thread = None

        if space == ON:
            pump.on()
            send_to_client("Spraying")

        if space == OFF:
            pump.off()
            send_to_client("Stop spraying...")

    except Exception as e:
        send_to_client("ERROR OCCURED: " + repr(e))


def handle_commands():
    """
    Establishes handshake with TCP Client and listens to any commands sent from the client.
    """
    global client_socket
    while True:
        try:
            client_socket, tcp_address = commands_socket.accept()
            print(f"Command center connected at {tcp_address}.")
            send_to_client("Connection established.")
            while True:
                try:
                    data = client_socket.recv(9, MSG_WAITALL)
                    if data:
                        # print(data)
                        print("data is " + get_most_recent(data))
                        execute_commands(get_most_recent(data))
                    if not data:
                        print("Commands disconnected from control center: No data")
                        break
                except KeyboardInterrupt:
                    print("Commands disconnected from control center: Keyboard Interrupt exception")
                    client_socket.close()
                    clean_up()
                    sys.exit(0)
                # except:
                #    print("Commands disconnected from control center: Failed to receive exception")
                #    clean_up()
                #    break
        except KeyboardInterrupt:
            print("Server hard-stopped with CTRL + C.")
            client_socket.close()
            clean_up()
            sys.exit(0)


def handle_video():
    """
    Starts the PiCamera and sends video feed from the camera to TCP client.
    """

    picam2 = Picamera2()
    # (3280, 2646), (1920, 1080), (1640, 1232), (640, 480)
    picam2.configure(picam2.create_preview_configuration(
        main={"format": 'XRGB8888', "size": (1640, 1232)}))  # "libcamera-hello -t 1 --nopreview" for all resolutions
    picam2.start()

    while True:
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
                clean_up()
                sys.exit(0)
            except:
                print("Video control disconnected from control center")
                break


BUFF_SIZE = 65536

HOST = "169.254.196.32"
# HOST = "172.20.10.7"
# HOST = "10.42.0.1"  # Standard loopback interface address (localhost)
# Pi server = 172.20.10.3 / 10.42.0.1

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
commands_thread.start()

video_thread = threading.Thread(target=handle_video, args=())
video_thread.start()

print("Server online...")

commands_thread.join()
video_thread.join()

