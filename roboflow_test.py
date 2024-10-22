from inference.models.utils import get_roboflow_model
import cv2


def update_nozzle(x_target, y_target):
    step = 5
    global nozzle_x
    global nozzle_y
    dx = x_target - nozzle_x
    dy = y_target - nozzle_y

    if abs(dx) >= step:
        x_next = nozzle_x + (step if dx > 0 else -step)
    else:
        x_next = x_target

    if abs(dy) >= step:
        y_next = nozzle_y + (step if dy > 0 else -step)
    else:
        y_next = y_target

    nozzle_x = x_next
    nozzle_y = y_next


# Roboflow model
model_name = "deteksiasapdanapi" # FIRE
model_version = "4"

# model_name = "fire-detection-ah0vk"   # CANDLE
# model_version = "1"

# MINE
# model_name = "fire-smoke-detection-eozii-nfuzs-vgo4cz"
# model_version = "2"

# TEST
# model_name = "people-detection-o4rdr"
# model_version = "7"

# Open the default camera (usually the built-in webcam)
cap = cv2.VideoCapture(0)

# Check if the webcam is opened successfully
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Get Roboflow face model (this will fetch the model from Roboflow)
model = get_roboflow_model(
    model_id="{}/{}".format(model_name, model_version),
    # Replace ROBOFLOW_API_KEY with your Roboflow API Key
    api_key="NHxBSfWHlHDOQC07yyLm"
)

radius = 3
thickness = -1
color = (255, 0, 0) # BGR

width = cap.get(3)
height = cap.get(4)

nozzle_x = width // 2
nozzle_y = height // 2

target_x = width // 2
target_y = height // 2

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()

    # If the frame was read successfully, display it
    if ret:
        # Run inference on the frame
        results = model.infer(image=frame,
                              confidence=0.5,
                              iou_threshold=0.5)

        # Plot image with face bounding box (using opencv)
        if results[0].predictions:
            prediction = results[0].predictions[0]
            class_name = prediction.class_name
            confidence = prediction.confidence
            print(prediction)
            print(class_name)

            x_center = int(prediction.x)
            y_center = int(prediction.y)
            width = int(prediction.width)
            height = int(prediction.height)

            # Calculate top-left and bottom-right corners from center, width, and height
            x0 = x_center - width // 2
            y0 = y_center - height // 2
            x1 = x_center + width // 2
            y1 = y_center + height // 2

            cv2.rectangle(frame, (x0, y0), (x1, y1), (255, 255, 0), 5)
            cv2.circle(frame, (x_center, y_center), radius, color, thickness)
            target_x = x_center
            target_y = y_center
            cv2.putText(frame, "Fire", (x0, y0 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)

        update_nozzle(target_x, target_y)
        cv2.circle(frame, (int(nozzle_x), int(nozzle_y)), radius, (0, 105, 255), thickness)
        # Display the resulting frameq
        cv2.imshow('Webcam Feed', frame)

        # Press 'q' to quit the video window
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        print("Error: Could not read frame.")
        break

# When everything is done, release the capture and destroy all windows
cap.release()
cv2.destroyAllWindows()