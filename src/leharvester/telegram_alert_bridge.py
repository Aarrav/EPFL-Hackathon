#!/usr/bin/env python3
"""Telegram bridge for the LeRobot ESP32 hall-sensor dashboard.

The bridge connects to the same ESP32 WebSocket stream as the dashboard and
sends Telegram messages for scheduled status reports, operator commands, and
alert conditions. It intentionally keeps the Telegram bot token out of the
browser dashboard and out of the ESP32 firmware.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import socket
import ssl
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import config as _project_config  # Loads repo-level .env before parsing env vars.


DEFAULT_WS_URL = "ws://10.183.143.188/ws"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        raise SystemExit(f"{name} must be an integer, got {value!r}")


def env_float(name: str) -> Optional[float]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        raise SystemExit(f"{name} must be a number, got {value!r}")


def now_label() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "unknown"
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


@dataclass
class Config:
    ws_url: str
    telegram_bot_token: str
    telegram_chat_id: str
    farm_name: str
    dry_run: bool
    status_interval_seconds: int
    reconnect_seconds: int
    stale_data_seconds: int
    stuck_seconds: int
    no_activity_seconds: int
    alert_repeat_seconds: int
    command_poll_seconds: int
    telegram_timeout_seconds: int
    farm_lat: Optional[float]
    farm_lon: Optional[float]
    rain_probability_threshold: int
    rain_lookahead_hours: int
    weather_check_seconds: int


def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description="Send LeRobot ESP32 WebSocket status and alerts to Telegram."
    )
    parser.add_argument("--ws-url", default=os.getenv("ESP32_WS_URL", DEFAULT_WS_URL))
    parser.add_argument("--farm-name", default=os.getenv("FARM_NAME", "LeRobot Harvester"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=env_bool("TELEGRAM_DRY_RUN", False),
        help="Print Telegram messages instead of sending them.",
    )
    parser.add_argument(
        "--status-interval-seconds",
        type=int,
        default=env_int("STATUS_INTERVAL_SECONDS", 7200),
    )
    parser.add_argument(
        "--stuck-seconds",
        type=int,
        default=env_int("GRIPPER_STUCK_SECONDS", 30),
    )
    parser.add_argument(
        "--no-activity-seconds",
        type=int,
        default=env_int("NO_ACTIVITY_SECONDS", 1800),
    )
    args = parser.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    dry_run = bool(args.dry_run)
    if not dry_run and (not token or not chat_id):
        raise SystemExit(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, or run with TELEGRAM_DRY_RUN=1."
        )

    return Config(
        ws_url=args.ws_url,
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        farm_name=args.farm_name,
        dry_run=dry_run,
        status_interval_seconds=max(60, args.status_interval_seconds),
        reconnect_seconds=env_int("RECONNECT_SECONDS", 5),
        stale_data_seconds=env_int("STALE_DATA_SECONDS", 15),
        stuck_seconds=max(5, args.stuck_seconds),
        no_activity_seconds=max(60, args.no_activity_seconds),
        alert_repeat_seconds=env_int("ALERT_REPEAT_SECONDS", 3600),
        command_poll_seconds=env_int("COMMAND_POLL_SECONDS", 5),
        telegram_timeout_seconds=env_int("TELEGRAM_TIMEOUT_SECONDS", 15),
        farm_lat=env_float("FARM_LAT"),
        farm_lon=env_float("FARM_LON"),
        rain_probability_threshold=env_int("RAIN_PROBABILITY_THRESHOLD", 70),
        rain_lookahead_hours=env_int("RAIN_LOOKAHEAD_HOURS", 2),
        weather_check_seconds=env_int("WEATHER_CHECK_SECONDS", 1800),
    )


class TelegramBot:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.telegram_bot_token}/"
        self.update_offset: Optional[int] = None

    def _api(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.dry_run:
            return {"ok": True, "result": []}

        data = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(self.base_url + method, data=data, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(
                request, timeout=self.config.telegram_timeout_seconds
            ) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Telegram network error: {exc.reason}") from exc

        data = json.loads(body)
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {body}")
        return data

    def send_message(self, text: str) -> None:
        if self.config.dry_run:
            print(f"\n[DRY RUN Telegram message]\n{text}\n", flush=True)
            return
        self._api(
            "sendMessage",
            {
                "chat_id": self.config.telegram_chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
        )

    def poll_commands(self) -> List[str]:
        if self.config.dry_run or not self.config.telegram_bot_token:
            return []

        payload: Dict[str, Any] = {
            "timeout": 0,
            "allowed_updates": json.dumps(["message"]),
        }
        if self.update_offset is not None:
            payload["offset"] = self.update_offset

        data = self._api("getUpdates", payload)
        commands: List[str] = []
        for update in data.get("result", []):
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                self.update_offset = update_id + 1

            message = update.get("message") or {}
            chat = message.get("chat") or {}
            chat_id = str(chat.get("id", ""))
            if chat_id != str(self.config.telegram_chat_id):
                continue

            text = str(message.get("text", "")).strip()
            if text.startswith("/"):
                commands.append(text.split()[0].split("@", 1)[0].lower())
        return commands


class WebSocketError(RuntimeError):
    pass


class Esp32WebSocketClient:
    """Small RFC 6455 client for receiving JSON from the ESP32."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme not in {"ws", "wss"}:
            raise WebSocketError(f"Unsupported WebSocket URL: {self.url}")

        host = parsed.hostname
        if not host:
            raise WebSocketError(f"WebSocket URL is missing a host: {self.url}")

        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        raw_sock = socket.create_connection((host, port), timeout=10)
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(raw_sock, server_hostname=host)
        else:
            self.sock = raw_sock
        self.sock.settimeout(2)

        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        host_header = f"{host}:{port}" if parsed.port else host
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))

        header = self._read_http_header()
        if " 101 " not in header.split("\r\n", 1)[0]:
            raise WebSocketError(f"WebSocket upgrade failed: {header.splitlines()[0]}")

        accept_seed = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        expected_accept = base64.b64encode(hashlib.sha1(accept_seed.encode("ascii")).digest())
        if expected_accept.decode("ascii") not in header:
            raise WebSocketError("WebSocket upgrade returned an invalid accept key")

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self.sock.close()
        finally:
            self.sock = None

    def receive_json(self) -> Optional[Dict[str, Any]]:
        while True:
            frame = self._receive_frame()
            if frame is None:
                return None

            opcode, payload = frame
            if opcode == 0x1:
                return json.loads(payload.decode("utf-8"))
            if opcode == 0x8:
                raise WebSocketError("ESP32 closed the WebSocket")
            if opcode == 0x9:
                self._send_frame(0xA, payload)

    def _read_http_header(self) -> str:
        if self.sock is None:
            raise WebSocketError("WebSocket is not connected")

        chunks: List[bytes] = []
        total = 0
        while True:
            chunk = self.sock.recv(1)
            if not chunk:
                raise WebSocketError("Connection closed during WebSocket upgrade")
            chunks.append(chunk)
            total += 1
            if total > 8192:
                raise WebSocketError("WebSocket upgrade header is too large")
            if b"".join(chunks).endswith(b"\r\n\r\n"):
                return b"".join(chunks).decode("iso-8859-1")

    def _read_exact(self, size: int) -> bytes:
        if self.sock is None:
            raise WebSocketError("WebSocket is not connected")

        chunks: List[bytes] = []
        remaining = size
        while remaining:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise WebSocketError("ESP32 WebSocket disconnected")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _receive_frame(self) -> Optional[Tuple[int, bytes]]:
        try:
            header = self._read_exact(2)
        except socket.timeout:
            return None

        first, second = header[0], header[1]
        opcode = first & 0x0F
        length = second & 0x7F
        masked = bool(second & 0x80)

        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]

        mask_key = self._read_exact(4) if masked else b""
        payload = self._read_exact(length) if length else b""
        if masked:
            payload = bytes(byte ^ mask_key[index % 4] for index, byte in enumerate(payload))

        return opcode, payload

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if self.sock is None:
            raise WebSocketError("WebSocket is not connected")

        mask_key = secrets.token_bytes(4)
        length = len(payload)
        header = bytes([0x80 | opcode])
        if length < 126:
            header += bytes([0x80 | length])
        elif length < 65536:
            header += bytes([0x80 | 126]) + struct.pack("!H", length)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", length)
        masked = bytes(byte ^ mask_key[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(header + mask_key + masked)


@dataclass
class FarmState:
    farm_name: str
    count: int = 0
    plucked: bool = False
    cooldown_ms: int = 0
    cooldown_limit_ms: int = 5000
    uptime_ms: Optional[int] = None
    wifi_rssi: Optional[int] = None
    heap_free: Optional[int] = None
    ws_clients: Optional[int] = None
    ip: Optional[str] = None
    messages_rx: int = 0
    connected: bool = False
    connected_since: Optional[float] = None
    last_message_at: Optional[float] = None
    last_counter_change_at: Optional[float] = None
    magnet_started_at: Optional[float] = None
    alert_log: List[str] = field(default_factory=list)

    def apply_payload(self, payload: Dict[str, Any], seen_at: float) -> None:
        previous_count = self.count
        self.count = int(payload.get("count", self.count))
        self.plucked = bool(payload.get("plucked", self.plucked))
        self.cooldown_ms = int(payload.get("cooldown", self.cooldown_ms))
        self.cooldown_limit_ms = int(payload.get("cooldownMs", self.cooldown_limit_ms))
        self.uptime_ms = as_optional_int(payload.get("uptimeMs"), self.uptime_ms)
        self.wifi_rssi = as_optional_int(payload.get("wifiRssi"), self.wifi_rssi)
        self.heap_free = as_optional_int(payload.get("heapFree"), self.heap_free)
        self.ws_clients = as_optional_int(payload.get("wsClients"), self.ws_clients)
        self.ip = str(payload.get("ip", self.ip or ""))
        self.messages_rx += 1
        self.last_message_at = seen_at

        if self.connected_since is None:
            self.connected_since = seen_at
        if self.last_counter_change_at is None or self.count != previous_count:
            self.last_counter_change_at = seen_at
        if self.plucked and self.magnet_started_at is None:
            self.magnet_started_at = seen_at
        if not self.plucked:
            self.magnet_started_at = None

    def status_text(self, config: Config) -> str:
        data_age = None
        if self.last_message_at is not None:
            data_age = time.monotonic() - self.last_message_at

        sensor_label = "magnet detected / gripper engaged" if self.plucked else "ready / no magnet"
        remaining_ms = max(0, self.cooldown_limit_ms - self.cooldown_ms)
        cooldown_label = "ready" if remaining_ms == 0 else f"{remaining_ms / 1000:.1f}s remaining"

        lines = [
            f"[STATUS] {self.farm_name}",
            f"Time: {now_label()}",
            f"Harvest count: {self.count}",
            f"Sensor: {sensor_label}",
            f"Cooldown: {cooldown_label}",
            f"Bridge link: {'connected' if self.connected else 'disconnected'}",
            f"Last ESP32 data: {format_duration(data_age)} ago",
        ]

        if self.uptime_ms is not None:
            lines.append(f"ESP32 uptime: {format_duration(self.uptime_ms / 1000)}")
        if self.wifi_rssi is not None:
            lines.append(f"WiFi RSSI: {self.wifi_rssi} dBm")
        if self.ip:
            lines.append(f"ESP32 IP: {self.ip}")
        if self.heap_free is not None:
            lines.append(f"ESP32 free heap: {self.heap_free} bytes")
        if self.ws_clients is not None:
            lines.append(f"WebSocket clients: {self.ws_clients}")
        if self.alert_log:
            lines.append("Recent alerts:")
            lines.extend(f"- {entry}" for entry in self.alert_log[-3:])

        return "\n".join(lines)

    def remember_alert(self, severity: str, title: str) -> None:
        self.alert_log.append(f"{now_label()} [{severity}] {title}")
        self.alert_log = self.alert_log[-8:]


def as_optional_int(value: Any, fallback: Optional[int]) -> Optional[int]:
    if value is None:
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def safe_send_message(bot: TelegramBot, text: str) -> None:
    try:
        bot.send_message(text)
    except Exception as exc:
        print(f"[{now_label()}] Could not send Telegram message: {exc}", file=sys.stderr)


class AlertManager:
    def __init__(self, bot: TelegramBot, state: FarmState, config: Config) -> None:
        self.bot = bot
        self.state = state
        self.config = config
        self.active: Dict[str, str] = {}
        self.last_sent: Dict[str, float] = {}

    def send(
        self,
        code: str,
        severity: str,
        title: str,
        details: List[str],
        repeat: bool = True,
    ) -> None:
        current = time.monotonic()
        last = self.last_sent.get(code, 0)
        already_active = code in self.active
        if already_active and repeat and current - last < self.config.alert_repeat_seconds:
            return
        if already_active and not repeat:
            return

        self.active[code] = severity
        self.last_sent[code] = current
        self.state.remember_alert(severity, title)

        lines = [f"[{severity}] {self.config.farm_name}", title, f"Time: {now_label()}"]
        lines.extend(details)
        lines.append(f"Harvest count: {self.state.count}")
        self._safe_send("\n".join(lines))

    def recover(self, code: str, title: str, details: List[str]) -> None:
        if code not in self.active:
            return
        self.active.pop(code, None)
        self.state.remember_alert("RECOVERY", title)
        lines = [f"[RECOVERY] {self.config.farm_name}", title, f"Time: {now_label()}"]
        lines.extend(details)
        self._safe_send("\n".join(lines))

    def evaluate(self) -> None:
        current = time.monotonic()

        if self.state.connected and self.state.last_message_at is not None:
            silent_for = current - self.state.last_message_at
            if silent_for > self.config.stale_data_seconds:
                self.send(
                    "stale_data",
                    "WARNING",
                    "ESP32 is connected but sensor data stopped arriving.",
                    [f"No WebSocket payload for {format_duration(silent_for)}."],
                )
            else:
                self.recover(
                    "stale_data",
                    "Sensor data is flowing again.",
                    [f"Last payload arrived {format_duration(silent_for)} ago."],
                )

        if self.state.plucked and self.state.magnet_started_at is not None:
            held_for = current - self.state.magnet_started_at
            if held_for >= self.config.stuck_seconds:
                self.send(
                    "gripper_stuck",
                    "WARNING",
                    "Possible gripper or hall-sensor stuck condition.",
                    [
                        f"Magnet has stayed detected for {format_duration(held_for)}.",
                        "Ask the operator to inspect the gripper and clear any obstruction.",
                    ],
                )
        else:
            self.recover(
                "gripper_stuck",
                "Gripper/hall-sensor state returned to normal.",
                ["Magnet is no longer continuously detected."],
            )

        if self.state.last_counter_change_at is not None:
            idle_for = current - self.state.last_counter_change_at
            if idle_for >= self.config.no_activity_seconds:
                self.send(
                    "no_activity",
                    "WARNING",
                    "No new harvest count for longer than expected.",
                    [
                        f"Counter has not changed for {format_duration(idle_for)}.",
                        "Check whether the robot is paused, blocked, or missing fruit.",
                    ],
                )
            else:
                self.recover(
                    "no_activity",
                    "Harvest counter activity resumed.",
                    [f"Last count update was {format_duration(idle_for)} ago."],
                )

    def _safe_send(self, text: str) -> None:
        safe_send_message(self.bot, text)


class WeatherWatcher:
    def __init__(self, config: Config, alerts: AlertManager) -> None:
        self.config = config
        self.alerts = alerts

    def enabled(self) -> bool:
        return self.config.farm_lat is not None and self.config.farm_lon is not None

    def check(self) -> None:
        if not self.enabled():
            return

        query = urllib.parse.urlencode(
            {
                "latitude": self.config.farm_lat,
                "longitude": self.config.farm_lon,
                "hourly": "precipitation_probability",
                "forecast_hours": max(1, self.config.rain_lookahead_hours + 1),
                "timezone": "auto",
            }
        )
        url = f"https://api.open-meteo.com/v1/forecast?{query}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                forecast = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            print(f"[{now_label()}] Weather check failed: {exc}", file=sys.stderr)
            return

        hourly = forecast.get("hourly", {})
        probabilities = hourly.get("precipitation_probability") or []
        if not probabilities:
            return

        horizon = max(1, min(len(probabilities), self.config.rain_lookahead_hours + 1))
        max_probability = max(int(value or 0) for value in probabilities[:horizon])
        if max_probability >= self.config.rain_probability_threshold:
            self.alerts.send(
                "rain_risk",
                "WARNING",
                "Rain risk is high near the farm.",
                [
                    f"Precipitation probability reaches {max_probability}% "
                    f"in the next {self.config.rain_lookahead_hours}h.",
                    "Consider moving the robot to cover or pausing outdoor operation.",
                ],
            )
        else:
            self.alerts.recover(
                "rain_risk",
                "Rain risk is back below the configured threshold.",
                [f"Highest near-term probability is {max_probability}%."],
            )


def handle_commands(bot: TelegramBot, state: FarmState, config: Config) -> None:
    try:
        commands = bot.poll_commands()
    except Exception as exc:
        print(f"[{now_label()}] Telegram command polling failed: {exc}", file=sys.stderr)
        return

    for command in commands:
        if command in {"/start", "/help"}:
            safe_send_message(
                bot,
                "\n".join(
                    [
                        f"{config.farm_name} bot is online.",
                        "Commands:",
                        "/status - current robot and sensor state",
                        "/alerts - recent warning and recovery history",
                        "/help - show this help",
                    ]
                )
            )
        elif command == "/status":
            safe_send_message(bot, state.status_text(config))
        elif command == "/alerts":
            if state.alert_log:
                safe_send_message(
                    bot,
                    "Recent alerts:\n" + "\n".join(f"- {x}" for x in state.alert_log),
                )
            else:
                safe_send_message(bot, "No alerts recorded since the bridge started.")


def run(config: Config) -> None:
    state = FarmState(config.farm_name)
    bot = TelegramBot(config)
    alerts = AlertManager(bot, state, config)
    weather = WeatherWatcher(config, alerts)

    safe_send_message(
        bot,
        "\n".join(
            [
                f"[INFO] {config.farm_name} Telegram bridge online.",
                f"Listening to ESP32 WebSocket: {config.ws_url}",
                f"Periodic status interval: {format_duration(config.status_interval_seconds)}",
            ]
        )
    )

    next_status_at = time.monotonic() + config.status_interval_seconds
    next_command_poll_at = time.monotonic() + config.command_poll_seconds
    next_weather_check_at = time.monotonic()

    while True:
        client = Esp32WebSocketClient(config.ws_url)
        try:
            client.connect()
            state.connected = True
            state.connected_since = time.monotonic()
            alerts.recover(
                "connection_lost",
                "ESP32 WebSocket connection restored.",
                [f"Connected to {config.ws_url}."],
            )

            while True:
                payload = client.receive_json()
                if payload is not None:
                    state.apply_payload(payload, time.monotonic())

                alerts.evaluate()
                current = time.monotonic()

                if state.last_message_at is not None and current >= next_status_at:
                    safe_send_message(bot, state.status_text(config))
                    next_status_at = current + config.status_interval_seconds

                if current >= next_command_poll_at:
                    handle_commands(bot, state, config)
                    next_command_poll_at = current + config.command_poll_seconds

                if current >= next_weather_check_at:
                    weather.check()
                    next_weather_check_at = current + config.weather_check_seconds

        except KeyboardInterrupt:
            print("\nBridge stopped by operator.")
            return
        except Exception as exc:
            state.connected = False
            alerts.send(
                "connection_lost",
                "ERROR",
                "Lost connection to the ESP32 WebSocket.",
                [
                    f"WebSocket URL: {config.ws_url}",
                    f"Error: {exc}",
                    f"Retrying in {config.reconnect_seconds}s.",
                ],
            )
            time.sleep(config.reconnect_seconds)
        finally:
            client.close()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
