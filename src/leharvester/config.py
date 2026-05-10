"""Shared configuration and repository paths for LeHarvester scripts."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - only used before dependencies are installed.
    load_dotenv = None


REPO_ROOT = Path(__file__).resolve().parents[2]

if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env", override=False)


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {value!r}") from exc


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a number, got {value!r}") from exc


def env_float_list(name: str, default: list[float]) -> list[float]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return [float(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise SystemExit(f"{name} must be a comma-separated list of numbers") from exc


def env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


def require_path(path: Path, label: str) -> Path:
    if not path.exists():
        raise SystemExit(
            f"{label} not found at {path}. Update the corresponding value in .env."
        )
    return path


DATA_DIR = env_path("LEHARVESTER_DATA_DIR", REPO_ROOT / "data")
YOLO_MODEL_PATH = env_path("YOLO_MODEL_PATH", DATA_DIR / "yolo" / "my_model.pt")
CAPTURED_IMAGES_DIR = env_path("CAPTURED_IMAGES_DIR", DATA_DIR / "local_captures")
URDF_PATH = env_path(
    "SO101_URDF_PATH",
    REPO_ROOT / "hardware" / "urdf" / "SO101" / "so101_new_calib.urdf",
)

ROBOT_PORT = os.getenv("ROBOT_PORT", "COM3")
SO101_PORT = os.getenv("SO101_PORT", ROBOT_PORT)
ROBOT_ID = os.getenv("ROBOT_ID", "so100")
CAMERA_INDEX = env_int("CAMERA_INDEX", 1)
FRONT_CAMERA_INDEX = env_int("FRONT_CAMERA_INDEX", 0)
WRIST_CAMERA_INDEX = env_int("WRIST_CAMERA_INDEX", 1)
CAMERA_WIDTH = env_int("CAMERA_WIDTH", 640)
CAMERA_HEIGHT = env_int("CAMERA_HEIGHT", 480)
CAMERA_FPS = env_int("CAMERA_FPS", 30)

FRUIT_CLASSES = tuple(
    item.strip()
    for item in os.getenv("FRUIT_CLASSES", "red_fruit,yellow_fruit,green_fruit").split(",")
    if item.strip()
)
DETECTION_CONFIDENCE = env_float("DETECTION_CONFIDENCE", 0.5)

FRUIT_POSITIONS = {
    "red_fruit": [0.3, 0.2, 0.4],
    "yellow_fruit": [0.3, 0.0, 0.4],
    "green_fruit": [0.3, -0.2, 0.4],
}
DROP_POSITION = [0.2, 0.3, 0.3]
ORIENTATION = [1.0, 0.0, 0.0, 0.0]

GRIPPER_OPEN = env_int("GRIPPER_OPEN", 0)
GRIPPER_CUT = env_int("GRIPPER_CUT", 50)
GRIPPER_DROP = env_int("GRIPPER_DROP", 0)

GRIPPER_SERIAL_PORT = os.getenv("GRIPPER_SERIAL_PORT", "/dev/cu.usbmodem5AE60550891")
GRIPPER_BAUD_RATE = env_int("GRIPPER_BAUD_RATE", 1000000)
GRIPPER_SERVO_ID = env_int("GRIPPER_SERVO_ID", 254)
GRIPPER_GUI_OPEN = env_int("GRIPPER_GUI_OPEN", 2500)
GRIPPER_GUI_CLOSED_LIMIT = env_int("GRIPPER_GUI_CLOSED_LIMIT", 1750)
GRIPPER_MAX_PRESSURE_CAP = env_int("GRIPPER_MAX_PRESSURE_CAP", 180)

CAPTURE_TOTAL_IMAGES = env_int("CAPTURE_TOTAL_IMAGES", 100)
CAPTURE_INTERVAL_SECONDS = env_float("CAPTURE_INTERVAL_SECONDS", 5.0)

MODELS_DIR = env_path("LEHARVESTER_MODELS_DIR", REPO_ROOT / "models")
ACT_POLICY_PATH = env_path("ACT_POLICY_PATH", MODELS_DIR / "my_act_policy")
SMOLVLA_POLICY_PATH = env_path("SMOLVLA_POLICY_PATH", MODELS_DIR / "my_smolvla_policy")
POLICY_TO_TEST = os.getenv("POLICY_TO_TEST", "act").strip().lower()
POLICY_IMAGE_KEY = os.getenv("POLICY_IMAGE_KEY", "observation.images.laptop")
POLICY_TASK = os.getenv("POLICY_TASK", "pick the red fruit")
POLICY_TARGET_IMAGE_WIDTH = env_int("POLICY_TARGET_IMAGE_WIDTH", 224)
POLICY_TARGET_IMAGE_HEIGHT = env_int("POLICY_TARGET_IMAGE_HEIGHT", 224)
POLICY_STATE = env_float_list("POLICY_STATE", [0.0, -0.5, 1.2, 0.0, 0.5, 0.0, 1.0])
DEMO_DEFAULT_DURATION_SECONDS = env_int("DEMO_DEFAULT_DURATION_SECONDS", 30)
