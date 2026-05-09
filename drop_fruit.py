# drop_fruit.py - Move to drop position and drop fruit

import time
from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig
from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.model.kinematics import RobotKinematics
from lerobot.robots.so_follower.robot_kinematic_processor import InverseKinematicsEEToJoints
from lerobot.types import RobotAction

# Configuration
ROBOT_PORT = "COM3"
ROBOT_ID = "so100"
CAMERA_INDEX = 1
URDF_PATH = "SO101/so101_new_calib.urdf"

DROP_POSITION = [0.2, 0.3, 0.3]
ORIENTATION = [1.0, 0.0, 0.0, 0.0]
GRIPPER_DROP = 0

def move_to_position(robot, ik_processor, target_pos, obs):
    ee_action = RobotAction({
        "ee_pos": target_pos,
        "ee_ori": ORIENTATION,
        "gripper.pos": 50  # Keep cut
    })
    joint_action = ik_processor.process((ee_action, obs))
    robot.send_action(joint_action)
    print(f"Moved to drop position {target_pos}")
    time.sleep(2)
    return robot.get_observation()

def main():
    # Setup robot
    camera_config = {
        "camera": OpenCVCameraConfig(index_or_path=CAMERA_INDEX, width=640, height=480, fps=30),
    }
    robot_cfg = SO100FollowerConfig(port=ROBOT_PORT, id=ROBOT_ID, cameras=camera_config, use_degrees=True)
    robot = SO100Follower(robot_cfg)
    robot.connect()

    # Kinematics
    kinematics_solver = RobotKinematics(
        urdf_path=URDF_PATH,
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

    # Drop
    current_joints = {k: v for k, v in obs.items() if k.endswith('.pos')}
    drop_action = RobotAction(current_joints)
    drop_action["gripper.pos"] = GRIPPER_DROP
    robot.send_action(drop_action)
    print("Dropping...")
    time.sleep(1)

    robot.disconnect()
    print("Drop done")

if __name__ == "__main__":
    main()</content>
<parameter name="filePath">c:\Users\20242015\OneDrive - TU Eindhoven\Documents\EPFL hackathon\drop_fruit.py