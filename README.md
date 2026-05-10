# LeHarvester

LeHarvester is an EPFL hackathon prototype for a small fruit-harvesting robot. It combines:

- a LeRobot SO100/SO101 follower arm,
- a trained Ultralytics YOLO model for fruit detection,
- a custom tactile/cutting gripper,
- ESP32 hall-sensor telemetry for harvest counting,
- a browser dashboard,
- a Telegram alert bridge for remote monitoring.

The repository now keeps the hackathon code separate from upstream LeRobot so it is easier to install, modify, and explain.

## Repository Layout

```text
.
├── src/leharvester/          # Python package and command-line entry points
├── data/
│   ├── yolo/                 # YOLO model and training archive
│   └── captured_images/      # Sample captured images
├── firmware/
│   ├── esp32_hall_sensor/    # WebSocket harvest counter firmware
│   ├── esp32_indicator/      # ESP32-S3 NeoPixel/system check firmware
│   └── gripper_uno/          # Arduino Uno STS servo exercise firmware
├── dashboard/                # Static browser dashboard
├── hardware/
│   ├── cad/                  # CAD, STEP, STL, and SolidWorks files
│   ├── calibration/          # LeRobot leader/follower calibration JSON
│   └── urdf/                 # Place SO101 URDF files here
├── third_party/              # Optional ignored local third-party checkouts
├── requirements.txt          # pip install recipe
├── environment.yml           # conda environment recipe
└── .env.example              # Hardware and service configuration template
```

## Main Components

### Vision

The vision scripts use `data/yolo/my_model.pt` through Ultralytics YOLO. They can run live webcam inference, capture new dataset images, or detect fruits as part of the full robot pipeline.

Relevant commands:

```bash
leharvester-yolo-live
leharvester-detect
leharvester-capture-dataset
```

### Robot Pipeline

The robot pipeline uses LeRobot's `SO100Follower` API plus a placo-backed `RobotKinematics` solver. The current prototype maps detected fruit classes to fixed end-effector coordinates in `src/leharvester/config.py`.

Relevant commands:

```bash
leharvester-cut
leharvester-drop
leharvester-pipeline
leharvester-full-pipeline
```

`leharvester-full-pipeline` is the clearest end-to-end entry point: it detects a fruit, moves to the configured target position, actuates the cutter/gripper, moves to the drop position, and releases.

### Policy Demo Helpers

Two helper commands wrap local LeRobot policy checkpoints:

```bash
leharvester-demo
leharvester-policy-inference
```

`leharvester-demo` launches `lerobot-rollout` interactively for ACT or SmolVLA checkpoints. `leharvester-policy-inference` captures one camera frame, builds a LeRobot observation, and prints the predicted action for a local checkpoint.

### Tactile Gripper GUI

`leharvester-gripper-gui` opens a Tkinter panel for directly controlling and monitoring the tactile gripper servo over serial. It reads the servo load register and stops closing when the configured load threshold is reached.

### ESP32 Dashboard Telemetry

`firmware/esp32_hall_sensor` reads a hall sensor on `HALL_SENSOR_PIN`, increments a harvest counter on fresh magnet detections, and broadcasts JSON over WebSocket at `/ws`.

Example JSON fields:

```json
{
  "device": "LeRobot Harvester ESP32",
  "ip": "192.168.1.42",
  "count": 7,
  "plucked": false,
  "cooldown": 1200,
  "cooldownMs": 5000,
  "uptimeMs": 95000,
  "wifiRssi": -55,
  "heapFree": 224000,
  "wsClients": 1
}
```

The dashboard in `dashboard/lerobot_dashboard.html` consumes that stream. Open it directly in a browser, or pass a different WebSocket URL through the query string:

```text
dashboard/lerobot_dashboard.html?ws=ws://ESP32_IP/ws
```

### Telegram Bridge

`leharvester-telegram-bridge` connects to the same ESP32 WebSocket stream and sends status reports, alerts, and command responses through Telegram. It keeps the bot token out of the dashboard and firmware.

Supported bot commands:

```text
/status
/alerts
/help
```

It can also send optional rain-risk warnings using Open-Meteo when `FARM_LAT` and `FARM_LON` are configured.

## Setup

Python 3.12 is recommended because current LeRobot releases declare `requires-python >=3.12`.

### Option A: pip

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Option B: conda

```bash
conda env create -f environment.yml
conda activate leharvester
```

If OpenCV GUI windows fail to open after installing LeRobot, the headless OpenCV wheel may have won the import order. Reinstall the GUI build inside the environment:

```bash
pip install --force-reinstall opencv-python
```

## Configuration

Copy the example file and edit it for your machine:

```bash
cp .env.example .env
```

Important values:

- `ROBOT_PORT`: serial port for the LeRobot follower arm, for example `COM3`, `/dev/ttyACM0`, or `/dev/cu.usbmodem...`.
- `SO101_PORT`: serial port used by the `lerobot-rollout` demo launcher.
- `CAMERA_INDEX`: OpenCV camera index.
- `FRONT_CAMERA_INDEX` and `WRIST_CAMERA_INDEX`: camera indices used by `leharvester-demo`.
- `YOLO_MODEL_PATH`: defaults to `data/yolo/my_model.pt`.
- `DETECTION_CONFIDENCE`: YOLO confidence threshold for fruit detections.
- `SO101_URDF_PATH`: path to `so101_new_calib.urdf`.
- `ACT_POLICY_PATH` and `SMOLVLA_POLICY_PATH`: local policy checkpoint folders under ignored `models/` by default.
- `POLICY_IMAGE_KEY`, `POLICY_STATE`, and `POLICY_TASK`: observation settings for `leharvester-policy-inference`.
- `GRIPPER_SERIAL_PORT`: serial port for the tactile gripper GUI.
- `ESP32_WS_URL`: WebSocket URL for the ESP32 hall-sensor counter.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`: required unless `TELEGRAM_DRY_RUN=1`.

The repository does not currently include the SO101 URDF. Place it at:

```text
hardware/urdf/SO101/so101_new_calib.urdf
```

or point `SO101_URDF_PATH` to its real location.

## Running the Prototype

Start with the pieces independently before running the full pipeline.

1. Verify the camera and YOLO model:

   ```bash
   leharvester-yolo-live
   ```

2. Verify one-shot detection:

   ```bash
   leharvester-detect
   ```

3. Verify gripper actuation at the current robot pose:

   ```bash
   leharvester-cut
   leharvester-drop
   ```

4. Run the full sequence:

   ```bash
   leharvester-full-pipeline
   ```

The current fruit coordinates are fixed prototype values in `src/leharvester/config.py`. Calibrate those before running near real hardware.

To test local LeRobot policy checkpoints:

```bash
leharvester-policy-inference
leharvester-demo
```

## Firmware

Install PlatformIO through `requirements.txt` or use the VS Code PlatformIO extension.

### ESP32 Hall Sensor

Edit `firmware/esp32_hall_sensor/platformio.ini`:

```ini
build_flags =
    -D WIFI_SSID=\"YOUR_WIFI_SSID\"
    -D WIFI_PASSWORD=\"YOUR_WIFI_PASSWORD\"
    -D HALL_SENSOR_ACTIVE_HIGH=0
    -D HALL_SENSOR_COOLDOWN_MS=5000
```

Then flash:

```bash
cd firmware/esp32_hall_sensor
pio run --target upload
pio device monitor
```

Watch the serial monitor for the ESP32 IP address, then use `ws://ESP32_IP/ws` in the dashboard or `ESP32_WS_URL`.

### ESP32 Indicator

```bash
cd firmware/esp32_indicator
pio run --target upload
pio device monitor
```

### Arduino Uno Gripper Exercise

```bash
cd firmware/gripper_uno
pio run --target upload
```

Unplug the servo adapter from pins 0/1 while uploading to the Uno, then reconnect for runtime serial control.

## Telegram Bridge

Dry run mode prints messages without contacting Telegram:

```bash
TELEGRAM_DRY_RUN=1 leharvester-telegram-bridge
```

Real bot mode:

```bash
TELEGRAM_DRY_RUN=0 \
TELEGRAM_BOT_TOKEN=123456:token \
TELEGRAM_CHAT_ID=123456789 \
ESP32_WS_URL=ws://ESP32_IP/ws \
leharvester-telegram-bridge
```

## Known Prototype Limitations

- Fruit positions are class-based fixed coordinates, not camera-to-robot calibrated 3D positions.
- `SO101_URDF_PATH` must be supplied before IK commands can run.
- The YOLO dataset archive and sample captures are stored locally; fresh capture output defaults to `data/local_captures`, which is ignored by Git.
- Hardware commands can move real motors. Keep the robot clear, start with low-risk poses, and test individual steps before end-to-end runs.
- The dashboard uses browser webcam APIs for the camera panel and the ESP32 WebSocket only for sensor/counter telemetry.
- `models/` and `third_party/lerobot/` are intentionally ignored so large checkpoints and library checkouts stay local.

## Useful Upstream References

- LeRobot is installed from `requirements.txt`.
- If you need to hack on LeRobot itself, clone it locally into `third_party/lerobot/`; that path is ignored by Git on purpose.


## Dataset

Hugging Face dataset:

- **[LeHarvester All Tasks Merged Dataset](https://huggingface.co/datasets/shubhamt0802/all_tasks_merged)**