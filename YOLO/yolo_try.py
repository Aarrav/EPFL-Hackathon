import cv2
from ultralytics import YOLO

# 1. Load your YOLO11s model
# Ensure 'my_model.pt' is in the same folder as this script
model = YOLO("YOLO\my_model.pt")

# 2. Open the webcam (0 is usually the default USB camera)
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Press 'q' to quit the stream.")

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        break

    # 3. Run inference on the frame
    # stream=True is more memory-efficient for video
    results = model(frame, stream=True)

    # 4. Visualize the results on the frame
    for r in results:
        annotated_frame = r.plot()

    # 5. Display the resulting frame
    cv2.imshow("YOLO11s Live Inference", annotated_frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the capture and close windows
cap.release()
cv2.destroyAllWindows()