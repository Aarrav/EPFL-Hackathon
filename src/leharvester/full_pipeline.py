"""Combined detect, move, cut, and drop pipeline for the fruit harvester."""

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


def detect_fruit(model, cap):
    ret, frame = cap.read()
    if not ret:
        return None
    results = model(frame, stream=True)
    detections = []
    for r in results:
        for box in r.boxes:
            cls = int(box.cls)
            conf = float(box.conf)
            class_name = model.names[cls]
            if class_name in FRUIT_POSITIONS and conf > DETECTION_CONFIDENCE:
                detections.append((class_name, conf))
    if detections:
        detections.sort(key=lambda x: x[1], reverse=True)
        return detections[0][0]  # Best class
    return None


def move_to(robot, ik_processor, pos, obs, gripper_pos):
    ee_action = RobotAction(
        {
            "ee_pos": pos,
            "ee_ori": ORIENTATION,
            "gripper.pos": gripper_pos,
        }
    )
    joint_action = ik_processor.process((ee_action, obs))
    robot.send_action(joint_action)
    time.sleep(2)
    return robot.get_observation()


def cut(robot, obs):
    current_joints = {k: v for k, v in obs.items() if k.endswith(".pos")}
    cut_action = RobotAction(current_joints)
    cut_action["gripper.pos"] = GRIPPER_CUT
    robot.send_action(cut_action)
    time.sleep(1)


def drop(robot, obs):
    current_joints = {k: v for k, v in obs.items() if k.endswith(".pos")}
    drop_action = RobotAction(current_joints)
    drop_action["gripper.pos"] = GRIPPER_DROP
    robot.send_action(drop_action)
    time.sleep(1)


def main():
    model = YOLO(str(require_path(YOLO_MODEL_PATH, "YOLO model")))
    urdf_path = require_path(URDF_PATH, "SO101 URDF")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Camera error")
        return

    robot_cfg = SO100FollowerConfig(
        port=ROBOT_PORT,
        id=ROBOT_ID,
        cameras={
            "camera": OpenCVCameraConfig(
                index_or_path=CAMERA_INDEX,
                width=640,
                height=480,
                fps=30,
            )
        },
        use_degrees=True,
    )
    robot = SO100Follower(robot_cfg)
    connected = False

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

        obs = robot.get_observation()

        fruit = detect_fruit(model, cap)
        if not fruit:
            print("No fruit detected")
            return

        print(f"Detected {fruit}")
        target_pos = FRUIT_POSITIONS[fruit]
        obs = move_to(robot, ik_processor, target_pos, obs, GRIPPER_OPEN)
        cut(robot, obs)
        obs = move_to(robot, ik_processor, DROP_POSITION, obs, GRIPPER_CUT)
        drop(robot, obs)

        print("Done")
    finally:
        if connected:
            robot.disconnect()
        cap.release()


if __name__ == "__main__":
    main()
