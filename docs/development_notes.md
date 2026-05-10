# Development Notes

## Organization Decisions

- Hackathon-owned Python code lives in `src/leharvester` and is installed as an editable package.
- Upstream LeRobot lives in `third_party/lerobot` and is installed separately through `requirements.txt`.
- `third_party/lerobot` is ignored by Git. Keep it as a local working checkout only; install the released package through `requirements.txt` for normal use.
- Runtime assets are grouped under `data`, while mechanical assets are grouped under `hardware`.
- Embedded projects are grouped under `firmware` and remain independent PlatformIO projects.
- Browser-only UI lives under `dashboard`.

## Path Rules

Python scripts should import paths from `leharvester.config` rather than assuming the current working directory. This lets commands run from the repository root, from an installed console script, or from another shell location.

Use `.env` for machine-specific values such as serial ports, camera indices, the ESP32 WebSocket URL, Telegram secrets, and the SO101 URDF location.

Policy checkpoints belong under ignored `models/` by default. Use `ACT_POLICY_PATH` and `SMOLVLA_POLICY_PATH` if they live elsewhere.

## Calibration Work Still Needed

The current pipeline maps YOLO classes to fixed end-effector coordinates. A production version should replace this with a calibrated camera-to-robot transform and depth estimate or a known workspace fixture model.
