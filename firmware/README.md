# Firmware

This directory groups all embedded projects.

- `esp32_hall_sensor/`: ESP32 hall-sensor counter with a WebSocket JSON endpoint at `/ws`.
- `esp32_indicator/`: ESP32-S3 NeoPixel and serial system-check sketch.
- `gripper_uno/`: Arduino Uno servo exercise sketch for the STS gripper servo.

Each project is a PlatformIO project. From a project folder, use:

```bash
pio run
pio run --target upload
pio device monitor
```

For `esp32_hall_sensor`, edit the `build_flags` in `platformio.ini` for WiFi credentials, hall-sensor polarity, and debounce/cooldown:

```ini
-D WIFI_SSID=\"YOUR_WIFI_SSID\"
-D WIFI_PASSWORD=\"YOUR_WIFI_PASSWORD\"
-D HALL_SENSOR_ACTIVE_HIGH=0
-D HALL_SENSOR_COOLDOWN_MS=5000
```

`esp32_hall_sensor/legacy/` contains imported sketches kept for reference after their useful settings were folded into the main PlatformIO firmware.
