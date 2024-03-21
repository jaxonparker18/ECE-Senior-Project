import base64
import socket
import cv2
import time
import imutils

def run():
    video_path = 0

    BUFF_SIZE = 65536
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
    HOST = "localhost"
    PORT = 2101
    server_socket.bind((HOST, PORT))
    vid = cv2.VideoCapture(video_path)
    fps, st, frames_to_count, cnt = (0, 0, 20, 0)

    # stream video
    while True:
        msg, client_addr = server_socket.recvfrom(BUFF_SIZE)
        print(msg)
        WIDTH = 840
        while vid.isOpened():
            _, frame = vid.read()
            frame = imutils.resize(frame, width=WIDTH)
            encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            message = base64.b64encode(buffer)
            server_socket.sendto(message, client_addr)
            frame = cv2.putText(frame, str(fps), (10, 40), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.imshow("TRANSMITTING VIDEO", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                server_socket.close()
                break
            if cnt == frames_to_count:
                try:
                    fps = round(frames_to_count/(time.time()- st))
                    st = time.time()
                    cnt = 0
                except:
                    pass
            cnt += 1


if __name__ == "__main__":
    run()