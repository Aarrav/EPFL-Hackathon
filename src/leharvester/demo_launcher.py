"""Interactive launcher for LeRobot SO101 policy rollouts."""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import (
    ACT_POLICY_PATH,
    CAMERA_FPS,
    CAMERA_HEIGHT,
    CAMERA_WIDTH,
    DEMO_DEFAULT_DURATION_SECONDS,
    FRONT_CAMERA_INDEX,
    POLICY_TASK,
    SMOLVLA_POLICY_PATH,
    SO101_PORT,
    WRIST_CAMERA_INDEX,
)


@dataclass(frozen=True)
class ModelEntry:
    name: str
    path: Path
    is_vla: bool


def model_registry() -> list[ModelEntry]:
    return [
        ModelEntry(name="ACT", path=ACT_POLICY_PATH, is_vla=False),
        ModelEntry(name="SmolVLA", path=SMOLVLA_POLICY_PATH, is_vla=True),
    ]


def choose_model() -> ModelEntry:
    registry = model_registry()
    available = [model for model in registry if model.path.exists()]
    missing = [model for model in registry if not model.path.exists()]

    if not available:
        print("No local checkpoints found. Expected at least one of:")
        for model in registry:
            print(f"  - {model.name:8s} at {model.path}")
        raise SystemExit(1)

    print("Select a model:")
    for index, model in enumerate(available, start=1):
        tag = " (VLA, needs prompt)" if model.is_vla else ""
        print(f"  [{index}] {model.name}{tag}")
    for model in missing:
        print(f"  [-] {model.name}  (missing: {model.path})")

    while True:
        raw = input(f"Choice [1-{len(available)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(available):
            return available[int(raw) - 1]
        print("Invalid choice, try again.")


def ask_duration(default: int = DEMO_DEFAULT_DURATION_SECONDS) -> int:
    raw = input(f"Run for how many seconds? [default {default}]: ").strip()
    if not raw:
        return default
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    print(f"Invalid input, using default {default}s.")
    return default


def ask_task(default: str = POLICY_TASK) -> str:
    raw = input(f"Task prompt [default '{default}']: ").strip()
    return raw or default


def build_cameras_flag() -> str:
    """Return the --robot.cameras dict expected by lerobot-rollout."""

    return (
        "{"
        f" front: {{type: opencv, index_or_path: {FRONT_CAMERA_INDEX}, "
        f"width: {CAMERA_WIDTH}, height: {CAMERA_HEIGHT}, fps: {CAMERA_FPS}}},"
        f" wrist: {{type: opencv, index_or_path: {WRIST_CAMERA_INDEX}, "
        f"width: {CAMERA_WIDTH}, height: {CAMERA_HEIGHT}, fps: {CAMERA_FPS}}}"
        " }"
    )


def build_command(entry: ModelEntry, duration: int, task: str) -> list[str]:
    cmd = [
        "lerobot-rollout",
        "--strategy.type=base",
        f"--policy.path={entry.path}",
        "--robot.type=so101_follower",
        f"--robot.port={SO101_PORT}",
        f"--robot.cameras={build_cameras_flag()}",
        f"--task={task}",
        f"--duration={duration}",
    ]
    if entry.is_vla:
        cmd += [
            "--inference.type=rtc",
            "--inference.rtc.execution_horizon=10",
        ]
    return cmd


def main() -> None:
    entry = choose_model()
    duration = ask_duration()
    task = ask_task() if entry.is_vla else "demo"
    cmd = build_command(entry, duration, task)

    print("\nLaunching:")
    print("  " + " ".join(shlex.quote(part) for part in cmd))
    print()

    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError as exc:
        raise SystemExit(
            "ERROR: `lerobot-rollout` was not found on PATH. Install LeRobot "
            "with the `core_scripts` extra, then reactivate the environment."
        ) from exc

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
