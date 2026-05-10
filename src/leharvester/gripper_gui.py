"""Tkinter control panel for the tactile fruit gripper servo."""

from __future__ import annotations

import serial
import threading
import time
import tkinter as tk

from .config import (
    GRIPPER_BAUD_RATE,
    GRIPPER_GUI_CLOSED_LIMIT,
    GRIPPER_GUI_OPEN,
    GRIPPER_MAX_PRESSURE_CAP,
    GRIPPER_SERIAL_PORT,
    GRIPPER_SERVO_ID,
)


class FruitGripperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tactile Fruit Gripper v2.0")
        self.root.geometry("480x650")
        self.root.configure(bg="#0F0F0F")

        try:
            self.ser = serial.Serial(
                port=GRIPPER_SERIAL_PORT,
                baudrate=GRIPPER_BAUD_RATE,
                timeout=0.05,
            )
            self.connected = True
        except serial.SerialException as exc:
            print(f"Warning: could not open gripper serial port: {exc}")
            self.ser = None
            self.connected = False

        self.is_running = False
        self.is_holding = False
        self.current_target = GRIPPER_GUI_OPEN

        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # 1. LOAD MONITOR (Main Display)
        self.load_frame = tk.Frame(self.root, bg="#0F0F0F", pady=20)
        self.load_frame.pack(fill="x")

        self.load_display = tk.Label(
            self.load_frame,
            text="0",
            font=("Impact", 64),
            fg="#FFFFFF",
            bg="#0F0F0F",
        )
        self.load_display.pack()
        tk.Label(
            self.load_frame,
            text="CURRENT LOAD UNITS",
            font=("Helvetica", 10, "bold"),
            fg="#AAAAAA",
            bg="#0F0F0F",
        ).pack()

        # 2. FRUIT DETECTION INDICATOR (The "Holding" part)
        self.status_card = tk.Frame(self.root, bg="#1E1E1E", height=80)
        self.status_card.pack(fill="x", padx=30, pady=10)
        self.status_card.pack_propagate(False)

        self.status_text = tk.Label(
            self.status_card,
            text="READY / IDLE",
            font=("Helvetica", 14, "bold"),
            fg="#444444",
            bg="#1E1E1E",
        )
        self.status_text.pack(expand=True)

        # 3. CONTROLS CARD
        ctrl_card = tk.Frame(self.root, bg="#1E1E1E", padx=25, pady=25)
        ctrl_card.pack(fill="both", expand=True, padx=20, pady=10)

        # Threshold Slider
        tk.Label(
            ctrl_card,
            text="PRESSURE THRESHOLD (MAX 180)",
            fg="#00FFCC",
            bg="#1E1E1E",
            font=("Helvetica", 10, "bold"),
        ).pack(anchor="w")
        self.threshold_slider = tk.Scale(
            ctrl_card,
            from_=10,
            to=GRIPPER_MAX_PRESSURE_CAP,
            orient="horizontal",
            bg="#1E1E1E",
            fg="white",
            highlightthickness=0,
            troughcolor="#333333",
            activebackground="#00FFCC",
            font=("Helvetica", 10),
        )
        self.threshold_slider.set(80)
        self.threshold_slider.pack(fill="x", pady=(5, 25))

        # Speed Slider
        tk.Label(
            ctrl_card,
            text="GRIP SPEED",
            fg="#00FFCC",
            bg="#1E1E1E",
            font=("Helvetica", 10, "bold"),
        ).pack(anchor="w")
        self.speed_slider = tk.Scale(
            ctrl_card,
            from_=50,
            to=1000,
            orient="horizontal",
            bg="#1E1E1E",
            fg="white",
            highlightthickness=0,
            troughcolor="#333333",
            activebackground="#00FFCC",
            font=("Helvetica", 10),
        )
        self.speed_slider.set(300)
        self.speed_slider.pack(fill="x", pady=(5, 25))

        # 4. HIGH CONTRAST BUTTONS
        btn_frame = tk.Frame(ctrl_card, bg="#1E1E1E")
        btn_frame.pack(fill="x")

        # Release Button - Emerald Green
        self.btn_open = tk.Button(
            btn_frame,
            text="RELEASE",
            command=self.open_gripper,
            bg="#10B981",
            fg="black",
            font=("Helvetica", 12, "bold"),
            relief="flat",
            height=2,
            cursor="hand2",
            activebackground="#059669",
        )
        self.btn_open.pack(side="left", expand=True, fill="x", padx=5)

        # Grip Button - Electric Blue
        self.btn_close = tk.Button(
            btn_frame,
            text="GRIP FRUIT",
            command=self.start_close,
            bg="#3B82F6",
            fg="black",
            font=("Helvetica", 12, "bold"),
            relief="flat",
            height=2,
            cursor="hand2",
            activebackground="#2563EB",
        )
        self.btn_close.pack(side="left", expand=True, fill="x", padx=5)

        # E-Stop - Vibrant Red
        self.btn_stop = tk.Button(
            self.root,
            text="STOP SYSTEM",
            command=self.stop_all,
            bg="#EF4444",
            fg="black",
            font=("Helvetica", 11, "bold"),
            relief="flat",
            pady=15,
            cursor="hand2",
            activebackground="#DC2626",
        )
        self.btn_stop.pack(fill="x", padx=20, pady=20)

    # --- SERVO BACKEND ---
    def send_command(self, reg, params):
        if not self.connected or self.ser is None:
            return
        length = len(params) + 3
        packet = [0xFF, 0xFF, GRIPPER_SERVO_ID, length, 0x03, reg] + params
        packet.append(~(sum(packet[2:]) & 0xFF) & 0xFF)
        self.ser.write(bytearray(packet))

    def read_load(self):
        if not self.connected or self.ser is None:
            return 0
        try:
            self.ser.reset_input_buffer()
            packet = [0xFF, 0xFF, GRIPPER_SERVO_ID, 0x04, 0x02, 0x45, 0x02]
            packet.append(~(sum(packet[2:]) & 0xFF) & 0xFF)
            self.ser.write(bytearray(packet))
            res = self.ser.read(8)
            if len(res) == 8:
                return (res[5] + (res[6] << 8)) & 0x3FF
        except serial.SerialException:
            pass
        return 0

    def open_gripper(self):
        self.is_running = False
        self.is_holding = False
        self.status_text.config(text="READY / IDLE", fg="#444444", bg="#1E1E1E")
        self.status_card.config(bg="#1E1E1E")
        self.send_command(0x28, [1])
        self.move_to(GRIPPER_GUI_OPEN, 800)
        self.current_target = GRIPPER_GUI_OPEN

    def move_to(self, position, speed):
        pos_h, pos_l = divmod(int(position), 256)
        spd_h, spd_l = divmod(int(speed), 256)
        self.send_command(0x2A, [pos_l, pos_h, spd_l, spd_h])

    def start_close(self):
        if not self.is_running:
            self.is_running = True
            self.is_holding = False
            self.status_text.config(text="SCANNING...", fg="#FFFFFF", bg="#3B82F6")
            self.status_card.config(bg="#3B82F6")
            threading.Thread(target=self.close_process, daemon=True).start()

    def close_process(self):
        while self.is_running and self.current_target > GRIPPER_GUI_CLOSED_LIMIT:
            load = self.read_load()
            if load > self.threshold_slider.get():
                self.is_running = False
                self.is_holding = True
                break

            self.current_target -= 15
            self.move_to(self.current_target, self.speed_slider.get())
            time.sleep(0.03)

        if self.is_holding:
            self.status_text.config(
                text="FRUIT DETECTED - HOLDING",
                fg="#FFFFFF",
                bg="#10B981",
            )
            self.status_card.config(bg="#10B981")
        else:
            self.stop_all()

    def stop_all(self):
        self.is_running = False
        self.move_to(self.current_target, 0)
        if not self.is_holding:
            self.status_text.config(text="SYSTEM STOPPED", fg="#EF4444", bg="#1E1E1E")

    def update_loop(self):
        load = self.read_load()
        self.load_display.config(text=f"{load}")

        # Color Warning for main number
        if load > self.threshold_slider.get():
            self.load_display.config(fg="#10B981")
        elif load > self.threshold_slider.get() * 0.7:
            self.load_display.config(fg="#F59E0B")
        else:
            self.load_display.config(fg="#FFFFFF")

        self.root.after(50, self.update_loop)


def main():
    root = tk.Tk()
    FruitGripperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
