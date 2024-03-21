import base64
import socket
import cv2
import pickle
import struct
import time
import numpy as np


def run():
    BUFF_SIZE = 65536
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
    HOST = "localhost"
    PORT = 2101
    message = b'Hello'
    client_socket.sendto(message, (HOST, PORT))
    fps, st, frames_to_count, cnt = (0, 0, 20, 0)

    while True:
        packet,_ = client_socket.recvfrom(BUFF_SIZE)
        data = base64.b64decode(packet)
        npdata = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(npdata, 1)
        frame = cv2.putText(frame, str(fps), (10, 40), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imshow("RECEIVING VIDEO", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            client_socket.close()
            break
        if cnt == frames_to_count:
            try:
                fps = round(frames_to_count / (time.time() - st))
                st = time.time()
                cnt = 0
            except:
                pass
        cnt += 1


if __name__ == "__main__":
    run()