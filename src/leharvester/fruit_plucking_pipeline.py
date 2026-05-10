"""Single-pass YOLO driven fruit plucking pipeline."""

import time

import cv2
from ultralytics import YOLO

from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.model.kinematics import RobotKinematics
from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig
from lerobot.robots.so_follower.robot_kinematic_processor import InverseKinematicsEEToJoints
from lerobot.types import RobotAction

from .config import (
    CAMERA_INDEX,
    DETECTION_CONFIDENCE,
    DROP_POSITION,
    FRUIT_POSITIONS,
    GRIPPER_CUT,
    GRIPPER_DROP,
    GRIPPER_OPEN,
    ORIENTATION,
    ROBOT_ID,
    ROBOT_PORT,
    URDF_PATH,
    YOLO_MODEL_PATH,
    require_path,
)


def main():
    model = YOLO(str(require_path(YOLO_MODEL_PATH, "YOLO model")))
    urdf_path = require_path(URDF_PATH, "SO101 URDF")

    camera_config = {
        "camera": OpenCVCameraConfig(
            index_or_path=CAMERA_INDEX,
            width=640,
            height=480,
            fps=30,
        ),
    }
    robot_cfg = SO100FollowerConfig(
        port=ROBOT_PORT,
        id=ROBOT_ID,
        cameras=camera_config,
        use_degrees=True,
    )
    robot = SO100Follower(robot_cfg)
    connected = False

    # Open camera for YOLO (separate from robot camera for simplicity)
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    try:
        robot.connect()
        connected = True

        kinematics_solver = RobotKinematics(
            urdf_path=str(urdf_path),
            target_frame_name="gripper_frame_link",
            joint_names=list(robot.bus.motors.keys()),
        )
        ik_processor = InverseKinematicsEEToJoints(
            kinematics=kinematics_solver,
            motor_names=list(robot.bus.motors.keys()),
            initial_guess_current_joints=True,
        )

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
                    if class_name in FRUIT_POSITIONS and conf > DETECTION_CONFIDENCE:
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

            ee_action = RobotAction(
                {
                    "ee_pos": target_pos,
                    "ee_ori": ORIENTATION,
                    "gripper.pos": GRIPPER_OPEN,
                }
            )

            # Convert EE action to joint action using IK
            joint_action = ik_processor.process((ee_action, obs))

            # Send move action
            robot.send_action(joint_action)
            time.sleep(2)  # Wait for move
            obs = robot.get_observation()

            # Cut action
            cut_action = RobotAction({"gripper.pos": GRIPPER_CUT})
            # For cut, keep joints the same, just change gripper
            current_joints = {
                f"{motor}.pos": obs[f"{motor}.pos"] for motor in robot.bus.motors
            }
            cut_action.update(current_joints)
            robot.send_action(cut_action)
            time.sleep(1)  # Wait for cut

            # Move to drop position
            drop_ee_action = RobotAction(
                {
                    "ee_pos": DROP_POSITION,
                    "ee_ori": ORIENTATION,
                    "gripper.pos": GRIPPER_CUT,
                }
            )
            drop_joint_action = ik_processor.process((drop_ee_action, obs))
            robot.send_action(drop_joint_action)
            time.sleep(2)
            obs = robot.get_observation()

            # Drop action
            drop_action = RobotAction({"gripper.pos": GRIPPER_DROP})
            current_joints = {
                f"{motor}.pos": obs[f"{motor}.pos"] for motor in robot.bus.motors
            }
            drop_action.update(current_joints)
            robot.send_action(drop_action)
            time.sleep(1)

            print(f"Plucked {fruit_class}")

            # Optional: break after one or continue
            break

    finally:
        cap.release()
        if connected:
            robot.disconnect()


if __name__ == "__main__":
    main()
