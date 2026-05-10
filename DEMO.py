"""Interactive launcher for the SO-101 demo.

Wraps `lerobot-rollout` (the official lerobot CLI) so the operator just
answers a few prompts instead of typing a long command line.

Flow:
  1. Ask which model to run: ACT or SmolVLA.
  2. Ask how long to run (seconds).
  3. For SmolVLA only, ask for the natural-language task prompt.
  4. Shell out to `lerobot-rollout` with the right flags.

Prereqs (run once inside the activated lerobot conda env):
    pip install -e C:\\Users\\shubh\\EPFL_HACK\\lerobot[training]
    hf auth login

Run:
    python src/DEMO.py
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


# --------------------------------------------------------------------------- #
# Hardware + checkpoint config. Edit to match your setup.
# --------------------------------------------------------------------------- #

SO101_PORT = "COM5"                # <-- change to your SO-101 COM port
FRONT_CAM_INDEX = 0                # front camera (scene view)
WRIST_CAM_INDEX = 1                # wrist camera (close-range view)
CAM_WIDTH = 640
CAM_HEIGHT = 480
CAM_FPS = 30


@dataclass
class ModelEntry:
    name: str
    path: str
    is_vla: bool                   # True for SmolVLA (needs --task + RTC inference)


REGISTRY: list[ModelEntry] = [
    ModelEntry(
        name="ACT",
        path="./models/my_act_policy",
        is_vla=False,
    ),
    ModelEntry(
        name="SmolVLA",
        path="./models/my_smolvla_policy",
        is_vla=True,
    ),
]


# --------------------------------------------------------------------------- #
# Prompts.
# --------------------------------------------------------------------------- #

def choose_model() -> ModelEntry:
    available = [m for m in REGISTRY if Path(m.path).exists()]
    missing = [m for m in REGISTRY if not Path(m.path).exists()]

    if not available:
        print("No local checkpoints found. Expected at least one of:")
        for m in REGISTRY:
            print(f"  - {m.name:8s} at {m.path}")
        sys.exit(1)

    print("Select a model:")
    for i, m in enumerate(available, start=1):
        tag = " (VLA, needs prompt)" if m.is_vla else ""
        print(f"  [{i}] {m.name}{tag}")
    for m in missing:
        print(f"  [-] {m.name}  (missing: {m.path})")

    while True:
        raw = input(f"Choice [1-{len(available)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(available):
            return available[int(raw) - 1]
        print("Invalid choice, try again.")


def ask_duration(default: int = 30) -> int:
    raw = input(f"Run for how many seconds? [default {default}]: ").strip()
    if not raw:
        return default
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    print(f"Invalid input, using default {default}s.")
    return default


def ask_task(default: str = "pick the red fruit") -> str:
    raw = input(f"Task prompt [default '{default}']: ").strip()
    return raw or default


# --------------------------------------------------------------------------- #
# Command builder.
# --------------------------------------------------------------------------- #

def build_cameras_flag() -> str:
    """Return the --robot.cameras dict lerobot expects.

    Keys here (`front`, `wrist`) MUST match the camera keys used when the
    checkpoint was trained, e.g. `observation.images.front`.
    """
    cams = (
        "{"
        f" front: {{type: opencv, index_or_path: {FRONT_CAM_INDEX}, "
        f"width: {CAM_WIDTH}, height: {CAM_HEIGHT}, fps: {CAM_FPS}}},"
        f" wrist: {{type: opencv, index_or_path: {WRIST_CAM_INDEX}, "
        f"width: {CAM_WIDTH}, height: {CAM_HEIGHT}, fps: {CAM_FPS}}}"
        " }"
    )
    return cams


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
    # SmolVLA is a slow VLA — use Real-Time Chunking so the arm keeps
    # executing action chunks while the next chunk is being computed.
    if entry.is_vla:
        cmd += [
            "--inference.type=rtc",
            "--inference.rtc.execution_horizon=10",
        ]
    return cmd


# --------------------------------------------------------------------------- #
# Entry point.
# --------------------------------------------------------------------------- #

def main() -> None:
    entry = choose_model()
    duration = ask_duration()
    task = ask_task() if entry.is_vla else "demo"  # ACT ignores the prompt but the flag is still required

    cmd = build_command(entry, duration, task)

    print("\nLaunching:")
    print("  " + " ".join(shlex.quote(c) for c in cmd))
    print()

    # Hand off stdin/stdout so the rollout's own logs and any interactive
    # keybinds (e.g. Ctrl+C) behave normally.
    try:
        result = subprocess.run(cmd)
    except FileNotFoundError:
        print(
            "ERROR: `lerobot-rollout` not found on PATH.\n"
            "Activate your lerobot conda env and reinstall:\n"
            "  conda activate lerobot\n"
            "  pip install -e C:\\Users\\shubh\\EPFL_HACK\\lerobot[training]"
        )
        sys.exit(1)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
