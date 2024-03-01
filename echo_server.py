# echo-server.py

from socket import *
import datetime


def get_most_recent(data_bytes):
    string_data = data_bytes.decode('utf-8')
    return string_data[len(string_data) - 5 : len(string_data)]


HOST = "localhost"  # Standard loopback interface address (localhost)
PORT = 2100  # Port to listen on (non-privileged ports are > 1023)

with socket(AF_INET, SOCK_STREAM) as s:
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    while True:
        conn, addr = s.accept()
        print(f"Control center connected at {addr}.")
        while True:
            try:
                data = conn.recv(1024)
                if data:
                    print("data is " + get_most_recent(data))
                if not data:
                    print("Disconnected from control center")
                    break
            except:
                print("Disconnected from control center")
                break

