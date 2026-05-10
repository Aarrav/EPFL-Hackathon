"""Capture timed webcam images for YOLO dataset collection."""

from __future__ import annotations

import time

import cv2

from .config import (
    CAMERA_INDEX,
    CAPTURED_IMAGES_DIR,
    CAPTURE_INTERVAL_SECONDS,
    CAPTURE_TOTAL_IMAGES,
)


def main() -> None:
    CAPTURED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open USB camera.")
        return

    print(f"Live feed active. Capturing {CAPTURE_TOTAL_IMAGES} images...")
    print("Press 'q' to quit early.")

    count = 0
    last_capture_time = time.time()

    try:
        while count < CAPTURE_TOTAL_IMAGES:
            ret, frame = cap.read()
            if not ret:
                break

            display_frame = frame.copy()
            status_text = f"Captured: {count}/{CAPTURE_TOTAL_IMAGES}"
            cv2.putText(
                display_frame,
                status_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            cv2.imshow("LeRobot Live Feed", display_frame)

            current_time = time.time()
            if current_time - last_capture_time >= CAPTURE_INTERVAL_SECONDS:
                count += 1
                filename = CAPTURED_IMAGES_DIR / f"img_{count:03d}.jpg"
                cv2.imwrite(str(filename), frame)
                print(f"[{count}/{CAPTURE_TOTAL_IMAGES}] Saved {filename}")
                last_capture_time = current_time

            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Interrupted by user.")
                break

        print("\nCapture sequence finished.")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera and windows closed.")


if __name__ == "__main__":
    main()
