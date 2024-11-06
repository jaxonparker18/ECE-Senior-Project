import cv2

# Initialize the video capture object to read from the webcam (or you can replace the 0 with a filename to track in a video)
cap = cv2.VideoCapture(0)

# Check if video opened successfully
if not cap.isOpened():
    print("Error: Could not open video source")
    exit()

# Read the first frame of the video
ret, frame = cap.read()
cv2.rectangle(frame, (10, 10), (50, 50), (255, 0, 0), 2)
if not ret:
    print("Error: Could not read video frame")
    exit()

# Let the user select the bounding box around the object to track
bbox = cv2.selectROI("Tracking", frame, False)
# bbox = ()
print(bbox)
# Initialize the CSRT tracker with the selected bounding box
# tracker = cv2.
tracker = cv2.legacy.TrackerMOSSE_create()
tracker.init(frame, bbox)

while True:
    # Capture a new frame from the video
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read video frame")
        break

    # Update the tracker with the new frame and obtain the updated bounding box
    success, bbox = tracker.update(frame)
    # bbox = [top left, top right, width, height]

    # If tracking was successful, draw the bounding box around the object
    if success:
        x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.putText(frame, "Tracking", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    else:
        # If tracking fails, display a message
        cv2.putText(frame, "Lost track", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # Display the resulting frame
    cv2.imshow("Tracking", frame)

    # Exit if the user presses the 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the video capture object and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()