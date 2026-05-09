"""
SO-101 Robot Connection Test
Tests connection, reads joint positions, moves to home position.
Run this FIRST before any other script.

Usage:
    python test_robot.py
    python test_robot.py --port /dev/ttyACM0       # Linux
    python test_robot.py --port /dev/tty.usbmodem* # Mac
"""

import argparse
import time

# ─── CONFIG ───────────────────────────────────────────────────────────────────

# Update this to your follower arm's port.
# Run `lerobot-find-port` to find it if unsure.
DEFAULT_PORT = "/dev/ttyUSB0"

# Home position (degrees). Arm points upright, gripper open.
# Tune these once you see the arm move — safe starting values below.
HOME_POSITION = {
    "shoulder_pan.pos":  0.0,   # center left/right
    "shoulder_lift.pos": 0.0,   # upright
    "elbow_flex.pos":    0.0,   # straight
    "wrist_flex.pos":    0.0,   # level
    "wrist_roll.pos":    0.0,   # no roll
    "gripper.pos":      50.0,   # half-open (0=closed, 100=open)
}

# How long to pause between incremental moves (seconds). Higher = safer.
MOVE_STEP_DELAY = 0.05

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main(port: str, robot_id: str):

    print("\n" + "="*55)
    print("  SO-101 Connection Test")
    print("="*55)

    # 1. Import
    try:
        from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig
        print("✓ LeRobot imported successfully")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        print("  → Run: pip install -e '.[feetech]' inside the lerobot repo")
        return

    # 2. Configure
    print(f"\n→ Connecting to port : {port}")
    print(f"→ Robot ID           : {robot_id}")

    config = SOFollowerRobotConfig(
        robot_type="so101_follower",
        id=robot_id,
        port=port,
    )

    # 3. Connect
    try:
        robot = SOFollower(config)
        robot.connect(calibrate=False)  # set calibrate=True if not yet calibrated
        print("✓ Robot connected\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nCommon fixes:")
        print("  • Wrong port    → run `lerobot-find-port`")
        print("  • No power      → check the arm's power supply LED")
        print("  • Permissions   → run `sudo chmod a+rw <port>` (Linux)")
        print("  • Calibration   → run `lerobot-calibrate --robot.type=so101_follower ...`")
        return

    try:

        # 4. Read current joint positions
        print("-"*55)
        print("CURRENT JOINT POSITIONS")
        print("-"*55)

        obs = robot.get_observation()

        joint_keys = [k for k in obs if k.endswith(".pos")]
        if not joint_keys:
            print("✗ No joint positions found in observation.")
            print(f"  Keys returned: {list(obs.keys())}")
        else:
            for key in sorted(joint_keys):
                val = obs[key]
                bar = make_bar(val, lo=-100, hi=100)
                print(f"  {key:<25} {val:>8.2f}°  {bar}")
            print()

        # 5. Sanity check — are positions reasonable?
        print("-"*55)
        print("SANITY CHECK")
        print("-"*55)

        all_ok = True
        for key in sorted(joint_keys):
            val = obs[key]
            if abs(val) > 150:
                print(f"  ⚠ {key} = {val:.1f}° — suspiciously large. Check calibration.")
                all_ok = False
            else:
                print(f"  ✓ {key} = {val:.1f}° — OK")

        if not all_ok:
            print("\n  → Re-run calibration: lerobot-calibrate --robot.type=so101_follower ...")
        print()

        # 6. Move to home
        print("-"*55)
        print("MOVING TO HOME POSITION")
        print("-"*55)
        print("  (Ctrl+C to abort at any time)\n")

        input("  ⚠ Make sure the arm workspace is clear. Press ENTER to continue...")

        print("\n  Moving slowly...")

        # Read current positions for each joint
        current = {k: obs[k] for k in joint_keys if k in HOME_POSITION}

        # Interpolate to home over N steps (safety)
        N_STEPS = 40
        for step in range(1, N_STEPS + 1):
            alpha = step / N_STEPS
            interpolated = {
                k: current[k] + alpha * (HOME_POSITION[k] - current[k])
                for k in HOME_POSITION
                if k in current
            }
            robot.send_action(interpolated)
            time.sleep(MOVE_STEP_DELAY)

            if step % 10 == 0:
                pct = int(alpha * 100)
                print(f"  [{pct:>3}%] Moving... {'█' * (pct // 5)}")

        print("\n  ✓ Reached home position\n")

        # 7. Verify final positions
        print("-"*55)
        print("FINAL JOINT POSITIONS")
        print("-"*55)

        final_obs = robot.get_observation()
        for key in sorted(joint_keys):
            target = HOME_POSITION.get(key, "—")
            actual = final_obs.get(key, float("nan"))
            err    = abs(actual - target) if isinstance(target, float) else "—"
            ok     = "✓" if isinstance(err, float) and err < 5.0 else "⚠"
            print(f"  {ok} {key:<25}  target={target:>6.1f}°  actual={actual:>7.2f}°")

        print()
        print("="*55)
        print("  Robot test complete. Ready to use.")
        print("="*55 + "\n")

    except KeyboardInterrupt:
        print("\n\n  ⚠ Aborted by user.")

    finally:
        robot.disconnect()
        print("  Robot disconnected safely.\n")


def make_bar(val, lo=-100, hi=100, width=20):
    """Simple ASCII bar showing joint position within range."""
    norm  = max(0.0, min(1.0, (val - lo) / (hi - lo)))
    filled = int(norm * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SO-101 connection test")
    parser.add_argument("--port",     default=DEFAULT_PORT,      help="Serial port of the follower arm")
    parser.add_argument("--robot_id", default="my_follower_arm", help="Robot ID (must match calibration)")
    args = parser.parse_args()

    main(port=args.port, robot_id=args.robot_id)