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
from gpiozero import PWMLED
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

# UART
serial_port = '/dev/ttyUSB0'  # debug port -> '/dev/ttyAMA10' | busted -> '/dev/ttyAMA0'
baud_rate = 115200
ser = serial.Serial(serial_port, baud_rate)

# GPIO MOTOR
left_motorA = PWMLED("BOARD11")
left_motorB = PWMLED("BOARD13")
right_motorA = PWMLED("BOARD16")
right_motorB = PWMLED("BOARD18")
left_motor = 0
right_motor = 1


def clean_up():
    global left_motorA
    global left_motorB
    global right_motorA
    global right_motorB
    global ser
    left_motorA.close()
    left_motorB.close()
    right_motorA.close()
    right_motorB.close()
    ser.close()


def get_most_recent(data_bytes):
    string_data = data_bytes.decode('utf-8')
    return string_data[len(string_data) - 9: len(string_data)]


def set_motor(left, right):
    global left_motorA
    global left_motorB
    global right_motorA
    global right_motorB

    if left == 0:
        left_motorA.value = 0
        left_motorB.value = 0
    elif left > 0:
        left_motorA.value = left
        left_motorB.value = 0
    else:
        left_motorA.value = 0
        left_motorB.value = abs(left)

    if right == 0:
        right_motorA.value = 0
        right_motorB.value = 0
    elif right > 0:
        right_motorA.value = 0
        right_motorB.value = right
    else:
        right_motorA.value = abs(right)
        right_motorB.value = 0


def send_to_uart(bits):
    for i in range(len(bits)):
        uart_command = str(bits[i]).encode('utf-8')
        ser.write(uart_command)
    print("sent to UART: " + bits)


def execute_commands(bits):
    print(bits)
    if len(bits) != 9:
        return

    w, a, s, d, space, up, down, left, right = bits
    w, a, s, d, space, up, down, left, right = int(w), int(a), int(s), int(d), int(space), int(up), int(down), int(
        left), int(right)

    # MOVEMENT
    if w and a:
        set_motor(0.5, 0.75)
    elif w and d:
        set_motor(0.75, 0.5)
    elif w and s:
        set_motor(0, 0)
    elif s and a:
        set_motor(-0.5, -0.75)
    elif s and d:
        set_motor(-0.75, -0.5)
    elif w:
        set_motor(0.75, 0.75)
        print("forward")
    elif s:
        set_motor(-0.75, -0.75)
    elif a:
        set_motor(-0.75, 0.75)
    elif d:
        set_motor(0.75, -0.75)
    else:
        set_motor(0, 0)

    # FIRING MECHANISM
    send_to_uart(bits[4:])


def handle_commands():
    while True:
        try:
            client_socket, tcp_address = commands_socket.accept()
            print(f"Control center connected at {tcp_address}.")
            client_socket.sendall((''.join("Connection established.")).encode('utf-8'))
            while True:
                try:
                    data = client_socket.recv(9, MSG_WAITALL)
                    if data:
                        # print(data)
                        # print("data is " + get_most_recent(data))
                        execute_commands(get_most_recent(data))
                    if not data:
                        print("Disconnected from control center")
                        break
                except KeyboardInterrupt:
                    print("Disconnected from control center")
                    client_socket.close()
                    clean_up()
                    sys.exit(0)
                except:
                    print("Disconnected from control center")
                    clean_up()
                    break
        except KeyboardInterrupt:
            print("Server hard-stopped with CTRL + C.")
            client_socket.close()
            clean_up()
            sys.exit(0)


def handle_video():
    picam2 = Picamera2()
    # (3280, 2646), (1920, 1080), (1640, 1232), (640, 480)
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1640, 1232)}))
    picam2.start()

    while True:
        client_sock, udp_address = video_socket.accept()
        print(f"Video feed connected at {udp_address}.")
        while True:
            im = picam2.capture_array()
            encoded, buffer = cv2.imencode('.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 70])
            message = base64.b64encode(buffer) + b'\0'
            client_sock.sendto(message, udp_address)


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

