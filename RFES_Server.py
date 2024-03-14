# echo-server.py
import socket
from socket import *
import sys
import datetime
import numpy
from time import sleep

# from gpiozero import PWMLED
# led = PWMLED("BOARD32")

HOST = "localhost"  # Standard loopback interface address (localhost)
# Pi server = 172.20.10.3
PORT = 2100  # Port to listen on (non-privileged ports are > 1023)

def get_most_recent(data_bytes):
    string_data = data_bytes.decode('utf-8')
    return string_data[len(string_data) - 9: len(string_data)]


def execute_commands(bits):
    print(bits)
    if len(bits) != 9:
        return

    execute_w(bits[0])
    execute_a(bits[1])
    execute_s(bits[2])
    execute_d(bits[3])
    execute_space(bits[4])
    execute_up(bits[5])
    execute_down(bits[6])
    execute_left(bits[7])
    execute_right(bits[8])


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


with socket(AF_INET, SOCK_STREAM) as s:
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print("Server online.")
    while True:
        try:
            conn, addr = s.accept()
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
                    s.close()
                    sys.exit(0)
                except:
                    print("Disconnected from control center")
                    break
        except KeyboardInterrupt:
            print("Server hard-stopped with CTRL + C.")
            s.close()
            sys.exit(0)
