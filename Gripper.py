import serial
import time

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/cu.usbmodem5AE60550891' 
BAUD_RATE = 1000000
SERVO_ID = 254  
GRIPPER_OPEN = 2500
GRIPPER_CLOSED_LIMIT = 1750

# --- LOAD THRESHOLD ---
# Adjust this based on your object. 
# 0-100 is usually 'free spinning'. 
# 300-600 is a firm grip. 1000+ is a very hard squeeze/stall.
LOAD_THRESHOLD = 10 

try:
    ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUD_RATE, timeout=0.05)
    print(f"Connected to {SERIAL_PORT}")
except Exception as e:
    print(f"Error: {e}"); exit()

def send_command(id, reg, params):
    length = len(params) + 3
    packet = [0xFF, 0xFF, id, length, 0x03, reg] + params
    checksum = ~(sum(packet[2:]) & 0xFF) & 0xFF
    packet.append(checksum)
    ser.write(bytearray(packet))
    ser.flush()

def move_to(id, position, speed=500):
    pos_h, pos_l = divmod(position, 256)
    spd_h, spd_l = divmod(speed, 256)
    send_command(id, 0x2A, [pos_l, pos_h, spd_l, spd_h])

def get_current_pos(id):
    packet = [0xFF, 0xFF, id, 0x04, 0x02, 0x38, 0x02]
    checksum = ~(sum(packet[2:]) & 0xFF) & 0xFF
    packet.append(checksum)
    ser.write(bytearray(packet))
    response = ser.read(8)
    if len(response) == 8:
        return response[5] + (response[6] << 8)
    return None

def read_current_load(id):
    """Reads the 0x45 Load Register"""
    packet = [0xFF, 0xFF, id, 0x04, 0x02, 0x45, 0x02]
    checksum = ~(sum(packet[2:]) & 0xFF) & 0xFF
    packet.append(checksum)
    
    ser.write(bytearray(packet))
    response = ser.read(8) 
    if len(response) == 8:
        load_val = response[5] + (response[6] << 8)
        # STS servos return values > 32768 for CCW direction load.
        # We use bitwise AND to get the magnitude of the load.
        return load_val & 0x3FF 
    return 0

def stop_servo(id):
    actual_pos = get_current_pos(id)
    if actual_pos is None: actual_pos = 0 
    move_to(id, actual_pos, 0) 
    print(f"\n[!] CONTACT DETECTED. Holding at position: {actual_pos}")

# --- EXECUTION ---
try:
    send_command(SERVO_ID, 0x28, [1]) # Torque Enable
    print("Opening Gripper...")
    move_to(SERVO_ID, GRIPPER_OPEN)
    time.sleep(1)

    current_target = GRIPPER_OPEN
    
    print(f"Closing... Stopping if Load > {LOAD_THRESHOLD}")
    
    while current_target > GRIPPER_CLOSED_LIMIT:
        loop_start = time.time()
        
        # 1. Read the actual load from the servo
        current_load = read_current_load(SERVO_ID)
        
        # 2. Print status
        print(f"Target: {current_target} | Actual Load: {current_load}    ", end='\r')

        # 3. Check if we hit something
        if current_load > LOAD_THRESHOLD:
            stop_servo(SERVO_ID)
            break
        
        # 4. Step forward
        current_target -= 15
        move_to(SERVO_ID, current_target, 300) # Moderate speed for better sensing
        
        # 5. Maintain ~30ms loop timing
        elapsed = time.time() - loop_start
        time.sleep(max(0, 0.03 - elapsed))

finally:
    ser.close()
    print("\nConnection closed.")