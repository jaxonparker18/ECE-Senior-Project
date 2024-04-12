import sys
import cv2
import torch
from matplotlib import pyplot as plt
import numpy as np

model = torch.hub.load('ultralytics/yolov5', 'yolov5s')

# image = 'https://ultralytics.com/images/zidane.jpg'
# results = model(image)
# results.print()

# plt.imshow(np.squeeze(results.render()))
# plt.show()

# Load in video capture
cam = cv2.VideoCapture(0)

while cam.isOpened():
    success, frame = cam.read()

    results = model(frame)

    cv2.imshow("Cam", np.squeeze(results.render()))

    if cv2.waitKey(1) == ord("q"):
        break
cam.release()
cv2.destroyAllWindows()
