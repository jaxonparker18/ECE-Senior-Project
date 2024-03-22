# echo-server.py
import socket
from socket import *
import sys
import datetime
import numpy
from time import sleep
import math


class Motor:
    def __init__(self):
        self.value = 0


# UART
import serial
serial_port = '/dev/ttySO'
baud_rate = 115200
ser = serial.Serial(serial_port, baud_rate)

from gpiozero import PWMLED

left_motorA = PWMLED("BOARD11")
left_motorB = PWMLED("BOARD13")
right_motorA = PWMLED("BOARD16")
right_motorB = PWMLED("BOARD18")
left_motor = 0
right_motor = 1

# right_motor = PWMLED("BOARD32")
# left_motor = PWMLED("BOARD33")

# left_motor = Motor()
# right_motor = Motor()

HOST = "localhost"  # Standard loopback interface address (localhost)
# Pi server = 172.20.10.3
PORT = 2100  # Port to listen on (non-privileged ports are > 1023)


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
        right_motorA.value = right
        right_motorB.value = 0
    else:
        right_motorA.value = 0
        right_motorB.value = abs(right)


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
    elif s:
        set_motor(-0.75, -0.75)
    elif a:
        set_motor(-0.75, 0.75)
    elif d:
        set_motor(0.75, -0.75)
    else:
        set_motor(0, 0)

    # FIRING MECHANISM
    uart_command = b''.join(bits[4:])
    print(str(uart_command) + "sent!")
    ser.write(uart_command)


def execute_w(cond):
    if cond == '1':
        print("forward")
        # ramping up speed
        # for v in numpy.arange(0, 1, 0.001):
        #     # led.value = v

        # led.value = 1

    else:
        # led.value = 0
        print("stop forward")


def execute_a(cond):
    if cond == '1':
        pass
    else:
        pass


def execute_s(cond):
    if cond == '1':
        pass
    else:
        pass


def execute_d(cond):
    if cond == '1':
        pass
    else:
        pass


def execute_space(cond):
    if cond == '1':
        pass
    else:
        pass


def execute_up(cond):
    if cond == '1':
        pass
    else:
        pass


def execute_down(cond):
    if cond == '1':
        pass
    else:
        pass


def execute_left(cond):
    if cond == '1':
        pass
    else:
        pass


def execute_right(cond):
    if cond == '1':
        pass
    else:
        pass


with socket(AF_INET, SOCK_STREAM) as soc:
    soc.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    soc.bind((HOST, PORT))
    soc.listen()
    print("Server online.")
    while True:
        try:
            conn, addr = soc.accept()
            print(f"Control center connected at {addr}.")
            conn.sendall((''.join("Connection established.")).encode('utf-8'))
            # initial command for STM
            ser.write(b'00000')
            print("init command: " + str(b'00000'))
            while True:
                try:
                    data = conn.recv(9, MSG_WAITALL)
                    if data:
                        # print(data)
                        # print("data is " + get_most_recent(data))
                        execute_commands(get_most_recent(data))
                    if not data:
                        print("Disconnected from control center")
                        ser.close()
                        break
                except KeyboardInterrupt:
                    print("Disconnected from control center")
                    soc.close()
                    ser.close()
                    sys.exit(0)
                except:
                    print("Disconnected from control center")
                    break
        except KeyboardInterrupt:
            print("Server hard-stopped with CTRL + C.")
            soc.close()
            ser.close()
            sys.exit(0)
