"""Run one LeRobot policy inference step on a live camera frame."""

from __future__ import annotations

import cv2
import numpy as np
import torch
from lerobot.configs import PreTrainedConfig
from lerobot.policies.factory import get_policy_class

from .config import (
    ACT_POLICY_PATH,
    CAMERA_INDEX,
    POLICY_IMAGE_KEY,
    POLICY_STATE,
    POLICY_TARGET_IMAGE_HEIGHT,
    POLICY_TARGET_IMAGE_WIDTH,
    POLICY_TASK,
    POLICY_TO_TEST,
    SMOLVLA_POLICY_PATH,
    require_path,
)


def preprocess_frame(frame: np.ndarray, device: str) -> torch.Tensor:
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_resized = cv2.resize(frame_rgb, (POLICY_TARGET_IMAGE_WIDTH, POLICY_TARGET_IMAGE_HEIGHT))
    frame_transposed = np.transpose(frame_resized, (2, 0, 1))
    image_tensor = torch.from_numpy(frame_transposed).float() / 255.0
    return image_tensor.unsqueeze(0).to(device)


def capture_frame() -> np.ndarray:
    cap = cv2.VideoCapture(CAMERA_INDEX)
    try:
        ret, frame = cap.read()
    finally:
        cap.release()

    if not ret:
        raise RuntimeError("Failed to grab a frame from the camera. Check CAMERA_INDEX.")
    return frame


def main() -> None:
    policy_name = POLICY_TO_TEST.lower()
    if policy_name not in {"act", "smolvla"}:
        raise SystemExit("POLICY_TO_TEST must be either 'act' or 'smolvla'.")

    local_path = ACT_POLICY_PATH if policy_name == "act" else SMOLVLA_POLICY_PATH
    local_path = require_path(local_path, f"{policy_name.upper()} policy")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Testing {policy_name.upper()} with real camera data on {device}...")

    config = PreTrainedConfig.from_pretrained(str(local_path))
    config.device = device
    policy_class = get_policy_class(config.type)
    policy = policy_class.from_pretrained(str(local_path), config=config)
    policy.eval()

    frame = capture_frame()
    image_tensor = preprocess_frame(frame, device)
    state_tensor = torch.tensor(POLICY_STATE).float().unsqueeze(0).to(device)

    observation = {
        POLICY_IMAGE_KEY: image_tensor,
        "observation.state": state_tensor,
    }
    if policy_name == "smolvla":
        observation["task_index"] = [POLICY_TASK]

    with torch.no_grad():
        action = policy.select_action(observation)

    print("\nSUCCESS: real-data inference complete.")
    print(f"Input image shape: {image_tensor.shape}")
    print(f"Input state shape: {state_tensor.shape}")
    print(f"Predicted action array:\n{action[0].cpu().numpy()}")


if __name__ == "__main__":
    main()
