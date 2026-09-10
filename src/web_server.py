#!/usr/bin/env python3
from flask import Flask, render_template
from flask_socketio import SocketIO
from pymavlink import mavutil
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Глобальні дані літака
plane_data = {
    'lat': -35.363262,
    'lon': 149.165237,
    'alt': 0,
    'heading': 0,
    'speed': 0,
    'throttle': 0,
    'battery': 0
}

def mavlink_worker():
    """Читає телеметрію і відправляє в браузер"""
    master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
    master.wait_heartbeat()
    print("MAVLink підключено!")

    while True:
        msg = master.recv_match(
            type=['GLOBAL_POSITION_INT', 'VFR_HUD', 'SYS_STATUS'],
            blocking=True,
            timeout=1
        )
        if msg:
            if msg.get_type() == 'GLOBAL_POSITION_INT':
                plane_data['lat'] = msg.lat / 1e7
                plane_data['lon'] = msg.lon / 1e7
                plane_data['alt'] = msg.relative_alt / 1000
                plane_data['heading'] = msg.hdg / 100
            elif msg.get_type() == 'VFR_HUD':
                plane_data['speed'] = msg.airspeed
                plane_data['throttle'] = msg.throttle
            elif msg.get_type() == 'SYS_STATUS':
                plane_data['battery'] = msg.battery_remaining

            socketio.emit('telemetry', plane_data)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Запускаємо MAVLink в окремому потоці
    t = threading.Thread(target=mavlink_worker)
    t.daemon = True
    t.start()

    print("Веб-сервер запущено на http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
