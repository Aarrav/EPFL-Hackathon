"""Run live YOLO inference from the configured camera."""

from __future__ import annotations

import cv2
from ultralytics import YOLO

from .config import CAMERA_INDEX, YOLO_MODEL_PATH, require_path


def main() -> None:
    model = YOLO(str(require_path(YOLO_MODEL_PATH, "YOLO model")))
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Press 'q' to quit the stream.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                break

            annotated_frame = frame
            for result in model(frame, stream=True):
                annotated_frame = result.plot()

            cv2.imshow("YOLO Live Inference", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
