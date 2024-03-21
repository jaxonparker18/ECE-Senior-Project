# echo-server.py
import socket
from socket import *
import sys
import datetime
import numpy
from time import sleep


class Motor:
    def __init__(self):
        self.value = 0


# from gpiozero import PWMLED
# right_motor = PWMLED("BOARD32")
# left_motor = PWMLED("BOARD33")
left_motor = Motor()
right_motor = Motor()

HOST = "localhost"  # Standard loopback interface address (localhost)
# Pi server = 172.20.10.3
PORT = 2100  # Port to listen on (non-privileged ports are > 1023)


def get_most_recent(data_bytes):
    string_data = data_bytes.decode('utf-8')
    return string_data[len(string_data) - 9: len(string_data)]


def set_motor(left, right):
    global left_motor
    global right_motor
    left_motor.value = left
    right_motor.value = right


def execute_commands(bits):
    print(bits)
    if len(bits) != 9:
        return

    w, a, s, d, space, up, down, left, right = bits
    w, a, s, d, space, up, down, left, right = int(w), int(a), int(s), int(d), int(space), int(up), int(down), \
                                               int(left), int(right)

    if w and a:
        set_motor(0.5, 1)
    elif w and d:
        set_motor(1, 0.5)
    elif w and s:
        set_motor(0, 0)
    elif s and a:
        pass
    elif s and d:
        pass
    elif w:
        set_motor(1, 1)
    elif s:
        pass
    elif a:
        set_motor(0, 1)
    elif d:
        set_motor(1, 0)


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
            while True:
                try:
                    data = conn.recv(9, MSG_WAITALL)
                    if data:
                        # print(data)
                        # print("data is " + get_most_recent(data))
                        execute_commands(get_most_recent(data))
                    if not data:
                        print("Disconnected from control center")
                        break
                except KeyboardInterrupt:
                    print("Disconnected from control center")
                    soc.close()
                    sys.exit(0)
                except:
                    print("Disconnected from control center")
                    break
        except KeyboardInterrupt:
            print("Server hard-stopped with CTRL + C.")
            soc.close()
            sys.exit(0)
