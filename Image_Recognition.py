import cv2

# Load in video capture
cam = cv2.VideoCapture(0)

while cam.isOpened():
    success, img = cam.read()

    cv2.imshow("Cam", img)
    if cv2.waitKey(1) == ord("q"):
        break

