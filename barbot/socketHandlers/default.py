from flask import request
from flask_socketio import emit
import logging

from barbot.config import config
from barbot.socket import socket, success, error
import barbot.wifi as wifi

logger = logging.getLogger(__name__)


@socket.on('connect')
def sock_connect():
    logger.info('connection opened from ' + request.remote_addr)
    emit('clientOptions', dict(config.items('client')))
    wifi.emitState()

@socket.on('disconnect')
def sock_disconnect():
    logger.info('connection closed from ' + request.remote_addr)

@socket.on_error_default  # handles all namespaces without an explicit error handler
def default_error_handler(e):
    logger.exception(e)
    return error('An internal error has ocurred!')
    
