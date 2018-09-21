
from flask_socketio import SocketIO

socket = SocketIO()

def success():
    return {'error': False}

def error(msg):
    return {'error': msg}

