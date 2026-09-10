#!/usr/bin/env python3
import math
import threading
import time
from flask import Flask, render_template
from flask_socketio import SocketIO
from pymavlink import mavutil

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Розширені глобальні дані літака
plane_data = {
    # Динаміка та стабілізація
    'roll': 0.0,
    'pitch': 0.0,
    'yaw': 0.0,
    'roll_rate': 0.0,
    'pitch_rate': 0.0,
    'target_roll': 0.0,
    'target_pitch': 0.0,
    'error_roll': 0.0,
    # Навігація та GPS
    'lat': -35.363262,
    'lon': 149.165237,
    'alt': 0.0,
    'heading': 0,
    'speed': 0.0,
    'throttle': 0,
    'battery': 0,
    'boot_time': 0.0,
}

def mavlink_worker():
    """Читає телеметрію з MAVLink і оновлює plane_data"""
    print("Підключення до MAV-LINK")
    master = mavutil.mavlink_connection('udpin:0.0.0.0:14551')
    master.wait_heartbeat()
    print("MAVLink підключено до веб-сервера!")

    # Запитуємо всі типи даних (включно з NAV_CONTROLLER_OUTPUT для target_roll/target_pitch)
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL,
        10,
        1,
    )
    
    while True:
        # non-blocking / timeout read
        msg = master.recv_match(blocking=True)
        if not msg:
            continue

        msg_type = msg.get_type()
        
        # Обробка необхідних повідомлень
        if msg_type == 'ATTITUDE':
            plane_data['roll'] = round(math.degrees(msg.roll), 1)
            plane_data['pitch'] = round(math.degrees(msg.pitch), 1)
            plane_data['roll_rate'] = round(math.degrees(msg.rollspeed), 1)
            plane_data['pitch_rate'] = round(math.degrees(msg.pitchspeed), 1)
            plane_data['yaw'] = round(math.degrees(msg.yaw), 1)
            plane_data['boot_time'] = round(msg.time_boot_ms / 1000.0, 1)
            plane_data['error_roll'] = round(plane_data['target_roll'] - plane_data['roll'], 1)

        elif msg_type == 'NAV_CONTROLLER_OUTPUT':
            plane_data['target_roll'] = round(msg.nav_roll, 1)
            plane_data['target_pitch'] = round(msg.nav_pitch, 1)
            plane_data['error_roll'] = round(plane_data['target_roll'] - plane_data['roll'], 1)

        elif msg_type == 'VFR_HUD':
            plane_data['speed'] = round(msg.airspeed, 1)
            plane_data['alt'] = round(msg.alt, 1)
            plane_data['heading'] = int(msg.heading)
            plane_data['throttle'] = msg.throttle

        elif msg_type == 'GLOBAL_POSITION_INT':
            plane_data['lat'] = msg.lat / 1e7
            plane_data['lon'] = msg.lon / 1e7

        elif msg_type == 'SYS_STATUS':
            plane_data['battery'] = msg.battery_remaining

        # Відправка телеметрії в веб-сокет після обробки будь-якого повідомлення,
        # а не тільки SYS_STATUS
        socketio.emit('telemetry', plane_data)
        socketio.sleep(0.02)  # обов'язково для eventlet/gevent!


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.start_background_task(target=mavlink_worker)
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
    print("Веб-сервер запущено на http://localhost:5001")