from pymavlink import mavutil
import math
from datetime import datetime

print("Підключення до SITL...")
master = mavutil.mavlink_connection('udpin:localhost:14550')

try:
    master.wait_heartbeat(timeout=5)
    print(f"Зв'язок встановлено! System ID: {master.target_system}")
except Exception:
    print("Помилка: Серцебиття не отримано за 5 секунд. Перевірте, чи запущено SITL!")
    exit(1)

master.mav.request_data_stream_send(
    master.target_system, 
    master.target_component, 
    mavutil.mavlink.MAV_DATA_STREAM_ALL, 
    10, 1)

try:
    roll_deg, pitch_deg = 0.0, 0.0
    target_roll, target_pitch, target_yaw = 0.0, 0.0, 0.0
    actual_roll_rate, actual_pitch_rate = 0.0, 0.0
    boot_time_sec = 0.0

    while True:
        msg = master.recv_match(type=['ATTITUDE', 'NAV_CONTROLLER_OUTPUT'], blocking=True, timeout=1.0)
        
        if msg is None:
            continue

        msg_type = msg.get_type()

        if msg_type == 'ATTITUDE':
            roll_deg = math.degrees(msg.roll)
            pitch_deg = math.degrees(msg.pitch)
            boot_time_sec = msg.time_boot_ms / 1000.0
            actual_roll_rate = math.degrees(msg.rollspeed)
            actual_pitch_rate = math.degrees(msg.pitchspeed)

        elif msg_type == 'NAV_CONTROLLER_OUTPUT':

            target_roll, target_pitch, target_yaw = msg.nav_roll, msg.nav_pitch, msg.nav_bearing


        now_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\r[{now_time} | SITL: {boot_time_sec:7.1f}s] [ROLL] Target: {target_roll:6.2f}° | Act: {roll_deg:6.2f}° | Rate: {actual_roll_rate:6.2f}°/s || [PITCH] Target: {target_pitch:6.2f}° | Act: {pitch_deg:6.2f}° | Rate: {actual_pitch_rate:6.2f}°/s", end="")


except KeyboardInterrupt:
    print("\nМоніторинг зупинено.")