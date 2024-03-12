# echo-server.py

from socket import *
import sys
import datetime
import numpy
from gpiozero import PWMLED
from time import sleep

HOST = "localhost"  # Standard loopback interface address (localhost)
PORT = 2100  # Port to listen on (non-privileged ports are > 1023)

led = PWMLED("BOARD32")


def get_most_recent(data_bytes):
    string_data = data_bytes.decode('utf-8')
    return string_data[len(string_data) - 5: len(string_data)]


def execute_commands(bits):
    # print(bits)
    if len(bits) != 5:
        return

    if bits[0] == '1':
        led.value = 1
        print("on")
    else:
        led.value = 0
        print("off")


with socket(AF_INET, SOCK_STREAM) as s:
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    while True:
        try:
            conn, addr = s.accept()
            print(f"Control center connected at {addr}.")
            conn.sendall((''.join("Connection established.")).encode('utf-8'))
            while True:
                try:
                    data = conn.recv(1024)
                    if data:
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
