"""Move the robot to the configured drop position and open the gripper."""

import time

from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.model.kinematics import RobotKinematics
from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig
from lerobot.robots.so_follower.robot_kinematic_processor import InverseKinematicsEEToJoints
from lerobot.types import RobotAction

from .config import (
    CAMERA_INDEX,
    DROP_POSITION,
    GRIPPER_CUT,
    GRIPPER_DROP,
    ORIENTATION,
    ROBOT_ID,
    ROBOT_PORT,
    URDF_PATH,
    require_path,
)


def move_to_position(robot, ik_processor, target_pos, obs):
    ee_action = RobotAction(
        {
            "ee_pos": target_pos,
            "ee_ori": ORIENTATION,
            "gripper.pos": GRIPPER_CUT,
        }
    )
    joint_action = ik_processor.process((ee_action, obs))
    robot.send_action(joint_action)
    print(f"Moved to drop position {target_pos}")
    time.sleep(2)
    return robot.get_observation()


def main():
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
        obs = move_to_position(robot, ik_processor, DROP_POSITION, obs)

        current_joints = {k: v for k, v in obs.items() if k.endswith(".pos")}
        drop_action = RobotAction(current_joints)
        drop_action["gripper.pos"] = GRIPPER_DROP
        robot.send_action(drop_action)
        print("Dropping...")
        time.sleep(1)
        print("Drop done")
    finally:
        if connected:
            robot.disconnect()


if __name__ == "__main__":
    main()
