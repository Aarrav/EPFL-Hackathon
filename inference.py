import cv2
import torch
import numpy as np
from lerobot.policies.factory import make_policy

# ==========================================
# 🛑 CONFIGURATION
# ==========================================
LOCAL_ACT_PATH = "./models/my_act_policy"
LOCAL_SMOLVLA_PATH = "./models/my_smolvla_policy"

POLICY_TO_TEST = "act" # change to "smolvla" to test the other
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CAMERA_INDEX = 0 # Change if using an external USB camera (e.g., 1 or 2)

# Check your config.json in the downloaded model folder for exact image size!
# LeRobot typically uses something like 224x224, 480x640, etc.
TARGET_IMAGE_SIZE = (224, 224) 

print(f"Testing {POLICY_TO_TEST.upper()} with REAL DATA on {DEVICE}...")

# 1. Load Local Policy
local_path = LOCAL_ACT_PATH if POLICY_TO_TEST == "act" else LOCAL_SMOLVLA_PATH
policy = make_policy(pretrained_path=local_path, device=DEVICE)
policy.eval()

# ==========================================
# 2. GRAB REAL HARDWARE DATA
# ==========================================

# --- A. Camera Processing ---
cap = cv2.VideoCapture(CAMERA_INDEX)
ret, frame = cap.read()
cap.release()

if not ret:
    raise RuntimeError("Failed to grab a frame from the camera! Check CAMERA_INDEX.")

# Preprocess the frame for PyTorch/LeRobot
# 1. BGR to RGB
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
# 2. Resize to what the model expects
frame_resized = cv2.resize(frame_rgb, TARGET_IMAGE_SIZE)
# 3. HWC to CHW (PyTorch expects channels first)
frame_transposed = np.transpose(frame_resized, (2, 0, 1))
# 4. Convert to float32 tensor and normalize to [0, 1]
real_image_tensor = torch.from_numpy(frame_transposed).float() / 255.0
# 5. Add the batch dimension: [1, C, H, W]
real_image_tensor = real_image_tensor.unsqueeze(0).to(DEVICE)

# --- B. Robot State Processing ---
# REPLACE THIS LIST with your actual SDK call, e.g., robot.get_joint_positions()
# Must match the dimension your model was trained on (e.g., 7 for 6 joints + 1 gripper)
real_joint_positions = [0.0, -0.5, 1.2, 0.0, 0.5, 0.0, 1.0] 
real_state_tensor = torch.tensor(real_joint_positions).float().unsqueeze(0).to(DEVICE)


# ==========================================
# 3. RUN INFERENCE
# ==========================================
observation = {
    # UPDATE "observation.images.laptop" to match your camera name in config.json!
    "observation.images.laptop": real_image_tensor, 
    "observation.state": real_state_tensor
}

if POLICY_TO_TEST == "smolvla":
    observation["task_index"] = ["pick up the block"]

with torch.no_grad():
    action = policy.select_action(observation)

print("\n✅ SUCCESS! Real-data inference complete.")
print(f"Input Image Shape: {real_image_tensor.shape}")
print(f"Input State Shape: {real_state_tensor.shape}")
print(f"Predicted Action Array:\n {action[0].cpu().numpy()}")