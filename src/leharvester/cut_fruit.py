"""Perform the gripper cutting action at the robot's current position."""

import time

from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig
from lerobot.types import RobotAction

from .config import CAMERA_INDEX, GRIPPER_CUT, ROBOT_ID, ROBOT_PORT


def main():
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
    try:
        robot.connect()
        connected = True
        obs = robot.get_observation()
        current_joints = {k: v for k, v in obs.items() if k.endswith(".pos")}

        cut_action = RobotAction(current_joints)
        cut_action["gripper.pos"] = GRIPPER_CUT
        robot.send_action(cut_action)
        print("Cutting...")
        time.sleep(1)
        print("Cut done")
    finally:
        if connected:
            robot.disconnect()


if __name__ == "__main__":
    main()
