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
# PI EXCLUSIVE
import serial
from gpiozero import Motor, Servo, PWMLED
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput


class Ser():
    def __init__(self):
        self.value = 0


class UpdateServoThread(threading.Thread):
    def __init__(self, servo, direction):
        super().__init__()
        self.servo = servo
        self.direction = direction
        self._stop_event = threading.Event()
        self.delay = DELAY
        self.new_val = 0

    def run(self):
        self.servo.on()
        global curr_x
        self.new_val = curr_x
        while not self._stop_event.is_set():
            if self.delay < DELAY:
                self.delay += 1
                continue
            if self.direction == LEFT:
                self.new_val += INCS
            elif self.direction == RIGHT:
                self.new_val -= INCS
            elif self.direction == UP:
                self.new_val += INCS
            elif self.direction == DOWN:
                self.new_val -= INCS
            if self.new_val > 0.3:
                self.new_val = 0.3
            if self.new_val < 0.04:
                self.new_val = 0.04
            self.servo.value = self.new_val
            curr_x = self.new_val
            self.delay = 0
            print("servo", curr_x)

    def stop(self):
        self.servo.off()
        self._stop_event.set()


# CONSTS
INCS = 0.01

DELAY = 1000000

UP = 0
DOWN = 1
LEFT = 2
RIGHT = 3

# UART
serial_port = '/dev/ttyAMA10'  # debug port -> '/dev/ttyAMA10', USB -> '/dev/USB0' | busted -> '/dev/ttyAMA0'
baud_rate = 115200
ser = serial.Serial(serial_port, baud_rate)

# GPIO MOTOR
left_motor = Motor("BOARD11", "BOARD13")
right_motor = Motor("BOARD18", "BOARD16")

# SERVOS
x_servo = PWMLED("BOARD40")
x_servo_thread = UpdateServoThread(x_servo, LEFT)
curr_x = 0

# SERVER
client_socket = None


def clean_up():
    """
    Closes any GPIO pins.
    """
    ser.close()


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
        w, a, s, d, space, up, down, left, right = int(w), int(a), int(s), int(d), int(space), int(up), int(down), int(
            left), int(right)

        # MOVEMENT
        if w and a:
            set_motor(0.10, 0.75)
            send_to_client("W and A executed.")
        elif w and d:
            set_motor(0.75, 0.10)
            send_to_client("W and D executed.")
        elif w and s:
            set_motor(0, 0)
            send_to_client("W and S executed.")
        elif s and a:
            set_motor(-0.25, -0.75)
            send_to_client("S and A executed.")
        elif s and d:
            set_motor(-0.75, -0.25)
            send_to_client("S and D executed.")
        elif w:
            set_motor(0.75, 0.75)
            send_to_client("W executed.")
        elif s:
            set_motor(-0.75, -0.75)
            send_to_client("S executed.")
        elif a:
            set_motor(-0.75, 0.75)
            send_to_client("A executed.")
        elif d:
            set_motor(0.75, -0.75)
            send_to_client("D executed.")
        else:
            set_motor(0, 0)
            send_to_client("RFES on standby.")

        # FIRING MECHANISM
        # send_to_uart(bits[4:])
        global x_servo_thread
        if left:
            if not x_servo_thread.is_alive():
                x_servo_thread = UpdateServoThread(x_servo, LEFT)
                x_servo_thread.start()
                return

        elif not left:
            if x_servo_thread.is_alive():
                x_servo_thread.stop()
                x_servo_thread.join()

        if right:
            if not x_servo_thread.is_alive():
                x_servo_thread = UpdateServoThread(x_servo, RIGHT)
                x_servo_thread.start()
                return

        elif not right:
            if x_servo_thread.is_alive():
                x_servo_thread.stop()
                x_servo_thread.join()

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
            # client_socket.sendall((''.join("Connection established.")).encode('utf-8'))
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
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1640, 1232)}))
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

HOST = "10.42.0.1"  # Standard loopback interface address (localhost)
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

