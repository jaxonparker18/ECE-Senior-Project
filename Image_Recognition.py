import sys
import cv2
import torch
from matplotlib import pyplot as plt
import numpy as np
import pathlib
import subprocess
import io
import contextlib

temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath

# model = torch.hub.load('ultralytics/yolov5', 'yolov5s')
model = torch.hub.load('ultralytics/yolov5', 'custom', path='fire_v5n50e.pt', force_reload=True)

# image = 'https://ultralytics.com/images/zidane.jpg'
# results = model(image)
# results.print()

# plt.imshow(np.squeeze(results.render()))
# plt.show()

# Load in video capture
cam = cv2.VideoCapture(0)

# circle attr
radius = 3
thickness = -1
color = (255, 0, 0)

while cam.isOpened():
    success, frame = cam.read()

    results = model(frame)
    # print(results.xyxy)
    # x1(pixels), y1(pixels), x2(pixels), y2(pixels), confidence, class
    # print(results.xyxy)
    # if len(results.xyxy[0]) > 0:
    #     x1 = results.xyxy[0][0][0]
    #     y1 = results.xyxy[0][0][1]
    #     x2 = results.xyxy[0][0][2]
    #     y2 = results.xyxy[0][0][3]
    #
    #     mid_x = (x1 + x2)/2
    #     mid_y = (y1 + y2)/2
    #
    #     center_coordinate = (int(mid_x), int(mid_y))
    #     frame = cv2.circle(frame, center_coordinate, radius, color, thickness)

    frame = np.squeeze(results.render())
    # frame = cv2.circle(frame, (int(x2), int(y2)), radius, color, thickness)
    cv2.imshow("Cam", frame)

    if cv2.waitKey(1) == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
