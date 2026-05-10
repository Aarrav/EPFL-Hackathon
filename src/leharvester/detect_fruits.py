"""Capture a camera frame and run YOLO fruit detection interactively."""

import cv2
from ultralytics import YOLO

from .config import (
    CAMERA_INDEX,
    DETECTION_CONFIDENCE,
    FRUIT_CLASSES,
    YOLO_MODEL_PATH,
    require_path,
)


def main():
    model = YOLO(str(require_path(YOLO_MODEL_PATH, "YOLO model")))

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Capturing image... Press 'c' to capture and detect, 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break

        cv2.imshow("Camera Feed", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            # Run detection
            results = model(frame, stream=True)
            detections = []
            for r in results:
                annotated_frame = r.plot()
                cv2.imshow("Detections", annotated_frame)
                cv2.waitKey(0)  # Wait for key to close detection window

                for box in r.boxes:
                    cls = int(box.cls)
                    conf = float(box.conf)
                    class_name = model.names[cls]
                    if class_name in FRUIT_CLASSES and conf > DETECTION_CONFIDENCE:
                        x1, y1, x2, y2 = box.xyxy[0]
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        detections.append({
                            'class': class_name,
                            'confidence': conf,
                            'center': (center_x, center_y),
                            'bbox': (x1, y1, x2, y2)
                        })

            if detections:
                # Sort by confidence
                detections.sort(key=lambda x: x['confidence'], reverse=True)
                print("Detections:")
                for det in detections:
                    print(f"  {det['class']}: conf {det['confidence']:.2f}, center {det['center']}")
                # Return the best detection for next steps
                best = detections[0]
                print(f"Best: {best['class']} at {best['center']}")
            else:
                print("No fruits detected")

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
