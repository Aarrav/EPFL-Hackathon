import cv2
import time
import os

# Configuration
TOTAL_IMAGES = 100
INTERVAL_SECONDS = 5
SAVE_DIRECTORY = "captured_images"

# Create the directory
if not os.path.exists(SAVE_DIRECTORY):
    os.makedirs(SAVE_DIRECTORY)

# Initialize camera
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Error: Could not open USB camera.")
    exit()

print(f"Live feed active. Capturing {TOTAL_IMAGES} images...")
print("Press 'q' to quit early.")

count = 0
last_capture_time = time.time()

try:
    while count < TOTAL_IMAGES:
        ret, frame = cap.read()
        if not ret:
            break

        # Display the live feed
        # We add some text to the screen so you know the status
        display_frame = frame.copy()
        status_text = f"Captured: {count}/{TOTAL_IMAGES}"
        cv2.putText(display_frame, status_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('LeRobot Live Feed', display_frame)

        # Check if 5 seconds have passed
        current_time = time.time()
        if current_time - last_capture_time >= INTERVAL_SECONDS:
            count += 1
            filename = os.path.join(SAVE_DIRECTORY, f"img_{count:03d}.jpg")
            cv2.imwrite(filename, frame)
            print(f"[{count}/{TOTAL_IMAGES}] Saved {filename}")
            
            # Reset the timer
            last_capture_time = current_time

        # Press 'q' to exit the live feed early
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Interrupted by user.")
            break

    print("\nCapture sequence finished.")

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Camera and windows closed.")