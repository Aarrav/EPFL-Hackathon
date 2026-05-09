import time
import cv2
import torch
from ultralytics import YOLO
from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig
from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.model.kinematics import RobotKinematics
from lerobot.processor import RobotProcessorPipeline, transition_to_robot_action
from lerobot.robots.so_follower.robot_kinematic_processor import InverseKinematicsEEToJoints
from lerobot.types import RobotAction

# Configuration - adjust these based on your setup
ROBOT_PORT = "COM3"  # Change to your robot's serial port
ROBOT_ID = "so100"  # Change to your robot's ID
CAMERA_INDEX = 1  # USB camera index, as in yolo_try.py
YOLO_MODEL_PATH = "YOLO/my_model.pt"
URDF_PATH = "SO101/so101_new_calib.urdf"  # Assume URDF is available

# Hardcoded end effector positions for each fruit (x, y, z in meters, relative to robot base)
# Adjust these based on your setup - measure the positions
FRUIT_POSITIONS = {
    'red_fruit': [0.3, 0.2, 0.4],  # Example position for red fruit
    'yellow_fruit': [0.3, 0.0, 0.4],  # Yellow fruit
    'green_fruit': [0.3, -0.2, 0.4],  # Green fruit
}

# Drop position (point B)
DROP_POSITION = [0.2, 0.3, 0.3]  # Example drop position

# Orientation for EE (quaternion: w, x, y, z) - assume facing down or appropriate
ORIENTATION = [1.0, 0.0, 0.0, 0.0]  # Identity quaternion

# Gripper positions
GRIPPER_OPEN = 0
GRIPPER_CUT = 50  # Position to activate cutter
GRIPPER_DROP = 0  # Open to drop fruit

def main():
    # Initialize YOLO model
    model = YOLO(YOLO_MODEL_PATH)

    # Robot configuration
    camera_config = {
        "camera": OpenCVCameraConfig(index_or_path=CAMERA_INDEX, width=640, height=480, fps=30),
    }
    robot_cfg = SO100FollowerConfig(port=ROBOT_PORT, id=ROBOT_ID, cameras=camera_config, use_degrees=True)
    robot = SO100Follower(robot_cfg)

    # Kinematics solver
    kinematics_solver = RobotKinematics(
        urdf_path=URDF_PATH,
        target_frame_name="gripper_frame_link",
        joint_names=list(robot.bus.motors.keys()),
    )

    # Inverse kinematics processor
    ik_processor = InverseKinematicsEEToJoints(
        kinematics=kinematics_solver,
        motor_names=list(robot.bus.motors.keys()),
        initial_guess_current_joints=True,
    )

    # Connect to robot
    robot.connect()

    # Open camera for YOLO (separate from robot camera for simplicity)
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    try:
        while True:
            # Capture image
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                continue

            # Run YOLO inference
            results = model(frame, stream=True)
            detections = []
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls)
                    conf = float(box.conf)
                    class_name = model.names[cls]
                    if class_name in FRUIT_POSITIONS and conf > 0.5:  # Confidence threshold
                        detections.append((class_name, conf, box.xyxy[0]))

            if not detections:
                print("No fruits detected")
                continue

            # Choose the fruit with highest confidence
            detections.sort(key=lambda x: x[1], reverse=True)
            fruit_class, _, _ = detections[0]
            target_pos = FRUIT_POSITIONS[fruit_class]
            print(f"Targeting {fruit_class} at position {target_pos}")

            # Get current observation for IK
            obs = robot.get_observation()

            # Create EE action (position + orientation)
            ee_action = RobotAction({
                "ee_pos": target_pos,
                "ee_ori": ORIENTATION,
                "gripper.pos": GRIPPER_OPEN  # Keep open initially
            })

            # Convert EE action to joint action using IK
            joint_action = ik_processor.process((ee_action, obs))

            # Send move action
            robot.send_action(joint_action)
            time.sleep(2)  # Wait for move

            # Cut action
            cut_action = RobotAction({
                "gripper.pos": GRIPPER_CUT
            })
            # For cut, keep joints the same, just change gripper
            current_joints = {f"{motor}.pos": obs[f"{motor}.pos"] for motor in robot.bus.motors}
            cut_action.update(current_joints)
            robot.send_action(cut_action)
            time.sleep(1)  # Wait for cut

            # Move to drop position
            drop_ee_action = RobotAction({
                "ee_pos": DROP_POSITION,
                "ee_ori": ORIENTATION,
                "gripper.pos": GRIPPER_CUT  # Keep cut position
            })
            drop_joint_action = ik_processor.process((drop_ee_action, obs))
            robot.send_action(drop_joint_action)
            time.sleep(2)

            # Drop action
            drop_action = RobotAction({
                "gripper.pos": GRIPPER_DROP
            })
            current_joints = {f"{motor}.pos": obs[f"{motor}.pos"] for motor in robot.bus.motors}
            drop_action.update(current_joints)
            robot.send_action(drop_action)
            time.sleep(1)

            print(f"Plucked {fruit_class}")

            # Optional: break after one or continue
            break

    finally:
        cap.release()
        robot.disconnect()

if __name__ == "__main__":
    main()</content>
<parameter name="filePath">c:\Users\20242015\OneDrive - TU Eindhoven\Documents\EPFL hackathon\fruit_plucking_pipeline.py