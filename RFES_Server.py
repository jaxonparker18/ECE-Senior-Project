# echo-server.py
import threading
from socket import *
import sys
import base64
import cv2
import time
import numpy as np
import imutils
# PI EXCLUSIVE
import serial
from gpiozero import PWMLED

# UART
serial_port = '/dev/ttyAMA0'
baud_rate = 115200
ser = serial.Serial(serial_port, baud_rate)

# GPIO MOTOR
left_motorA = PWMLED("BOARD11")
left_motorB = PWMLED("BOARD13")
right_motorA = PWMLED("BOARD16")
right_motorB = PWMLED("BOARD18")
left_motor = 0
right_motor = 1


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


def send_to_uart(bits):
    for i in range(len(bits)):
        uart_command = str(bits[i]).encode('utf-8')
        ser.write(uart_command)


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
    send_to_uart(bits[4:])

def handle_tcp():
    while True:
        try:
            client_socket, tcp_address = tcp_socket.accept()
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
                    ser.close()
                    sys.exit(0)
                except:
                    print("Disconnected from control center")
                    break
        except KeyboardInterrupt:
            print("Server hard-stopped with CTRL + C.")
            client_socket.close()
            ser.close()
            sys.exit(0)


def handle_udp(client_socket):
    vid = cv2.VideoCapture(0)   # webcam
    fps, st, frames_to_count, cnt = (0, 0, 20, 0)
    # # Configure the Raspberry Pi camera
    # camera = picamera.PiCamera()
    #
    # # Set camera resolution (optional)
    # camera.resolution = (640, 480)
    #
    # # Set up a stream for image capture
    # stream = io.BytesIO()
    #
    # # Start capturing video
    # camera.start_recording(stream, format='h264')
    #
    # try:
    #     while True:
    #         # Capture video frame
    #         stream.seek(0)
    #         data = stream.read()
    #
    #         # Send frame over UDP
    #         udp_socket.sendto(data, ("destination_IP", destination_port))
    #
    # finally:
    #     # Stop recording and clean up
    #     camera.stop_recording()
    #     camera.close()
    #     udp_socket.close()

    # stream video
    while True:
        msg, client_addr = client_socket.recvfrom(BUFF_SIZE)
        print(msg)
        WIDTH = 840
        while vid.isOpened():
            _, frame = vid.read()
            frame = imutils.resize(frame, width=WIDTH)
            encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            message = base64.b64encode(buffer)
            client_socket.sendto(message, client_addr)
            frame = cv2.putText(frame, str(fps), (10, 40), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.imshow("TRANSMITTING VIDEO", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                client_socket.close()
                break
            if cnt == frames_to_count:
                try:
                    fps = round(frames_to_count/(time.time() - st))
                    st = time.time()
                    cnt = 0
                except:
                    pass
            cnt += 1


BUFF_SIZE = 100000


HOST = "172.20.10.3"  # Standard loopback interface address (localhost)
# Pi server = 172.20.10.3

# TCP SOCKET
TCP_PORT = 2100  # Port to listen on (non-privileged ports are > 1023)
tcp_socket = socket(AF_INET, SOCK_STREAM)
tcp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
tcp_socket.bind((HOST, TCP_PORT))
tcp_socket.listen(0)

# UDP SOCKET
UDP_PORT = 2101  # Port to listen on (non-privileged ports are > 1023)
udp_socket = socket(AF_INET, SOCK_DGRAM)
udp_socket.setsockopt(SOL_SOCKET, SO_RCVBUF, BUFF_SIZE)
udp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
udp_socket.bind((HOST, UDP_PORT))

print("Server online...")

tcp_thread = threading.Thread(target=handle_tcp, args=())
tcp_thread.start()

udp_thread = threading.Thread(target=handle_udp, args=(udp_socket,))
udp_thread.start()

tcp_thread.join()
udp_thread.join()

