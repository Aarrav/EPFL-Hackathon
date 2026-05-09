# cut_fruit.py - Perform cutting action at current position

import time
from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig
from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.types import RobotAction

# Configuration
ROBOT_PORT = "COM3"
ROBOT_ID = "so100"
CAMERA_INDEX = 1

GRIPPER_OPEN = 0
GRIPPER_CUT = 50

def main():
    # Setup robot
    camera_config = {
        "camera": OpenCVCameraConfig(index_or_path=CAMERA_INDEX, width=640, height=480, fps=30),
    }
    robot_cfg = SO100FollowerConfig(port=ROBOT_PORT, id=ROBOT_ID, cameras=camera_config, use_degrees=True)
    robot = SO100Follower(robot_cfg)
    robot.connect()

    # Get current joints
    obs = robot.get_observation()
    current_joints = {k: v for k, v in obs.items() if k.endswith('.pos')}

    # Cut action
    cut_action = RobotAction(current_joints)
    cut_action["gripper.pos"] = GRIPPER_CUT
    robot.send_action(cut_action)
    print("Cutting...")
    time.sleep(1)

    robot.disconnect()
    print("Cut done")

if __name__ == "__main__":
    main()</content>
<parameter name="filePath">c:\Users\20242015\OneDrive - TU Eindhoven\Documents\EPFL hackathon\cut_fruit.py