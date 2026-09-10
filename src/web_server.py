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
    master = mavutil.mavlink_connection('udpin:localhost:14550')
    master.wait_heartbeat()
    print("MAVLink підключено до веб-сервера!")

    # Запитуємо потрібні типи даних
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,
        10,
        1,
    )
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_POSITION,
        5,
        1,
    )

    while True:
        msg = master.recv_match(
            type=[
                'ATTITUDE',
                'NAV_CONTROLLER_OUTPUT',
                'GLOBAL_POSITION_INT',
                'VFR_HUD',
                'SYS_STATUS',
            ],
            blocking=True,
            timeout=1.0,
        )

        if not msg:
            continue

        msg_type = msg.get_type()

        if msg_type == 'ATTITUDE':
            plane_data['roll'] = round(math.degrees(msg.roll), 2)
            plane_data['pitch'] = round(math.degrees(msg.pitch), 2)
            plane_data['yaw'] = round(math.degrees(msg.yaw), 2)
            plane_data['roll_rate'] = round(math.degrees(msg.rollspeed), 2)
            plane_data['pitch_rate'] = round(math.degrees(msg.pitchspeed), 2)
            plane_data['boot_time'] = round(msg.time_boot_ms / 1000.0, 1)

            # Оновлюємо помилку
            plane_data['error_roll'] = round(
                plane_data['target_roll'] - plane_data['roll'], 2
            )

        elif msg_type == 'NAV_CONTROLLER_OUTPUT':
            plane_data['target_roll'] = round(msg.nav_roll, 2)
            plane_data['target_pitch'] = round(msg.nav_pitch, 2)

        elif msg_type == 'GLOBAL_POSITION_INT':
            plane_data['lat'] = msg.lat / 1e7
            plane_data['lon'] = msg.lon / 1e7
            plane_data['alt'] = round(msg.relative_alt / 1000.0, 1)
            plane_data['heading'] = int(msg.hdg / 100)

        elif msg_type == 'VFR_HUD':
            plane_data['speed'] = round(msg.airspeed, 1)
            plane_data['throttle'] = msg.throttle

        elif msg_type == 'SYS_STATUS':
            plane_data['battery'] = msg.battery_remaining

        # Відправляємо оновлений стан у веб-інтерфейс
        socketio.emit('telemetry', plane_data)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    t = threading.Thread(target=mavlink_worker, daemon=True)
    t.start()

    print("Веб-сервер запущено на http://localhost:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)