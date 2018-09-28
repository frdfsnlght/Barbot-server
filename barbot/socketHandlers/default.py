from flask import request
from flask_socketio import emit
import logging

from barbot.config import config
from barbot.socket import socket, success, error
from barbot.events import bus

logger = logging.getLogger('Socket_Default')


@socket.on('connect')
def socket_connect():
    logger.info('connection opened from ' + request.remote_addr)
    emit('clientOptions', dict(config.items('client')))
    bus.emit('client:connect')

@socket.on('disconnect')
def socket_disconnect():
    logger.info('connection closed from ' + request.remote_addr)

@socket.on_error_default  # handles all namespaces without an explicit error handler
def default_error_handler(e):
    logger.exception(e)
    return error('An internal error has ocurred!')
    
