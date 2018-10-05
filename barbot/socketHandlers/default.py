from flask import request
from flask_socketio import emit
import logging

from ..config import config
from ..socket import socket, success, error
from ..bus import bus

logger = logging.getLogger('Socket_Default')


@socket.on('connect')
def _socket_connect():
    logger.info('connection opened from ' + request.remote_addr)
    emit('clientOptions', dict(config.items('client')))
    bus.emit('client:connect')

@socket.on('disconnect')
def _socket_disconnect():
    logger.info('connection closed from ' + request.remote_addr)
    bus.emit('client:disconnect')

@socket.on_error_default  # handles all namespaces without an explicit error handler
def _socket_default_error_handler(e):
    logger.exception(e)
    return error('An internal error has ocurred!')
    


@socket.on('toggleDispenserHold')
def _socket_toggleDispenserHold():
    bus.emit('barbot:toggleDispenserHold')
    return success()

@socket.on('startPumpSetup')
def _socket_startPumpSetup():
    bus.emit('barbot:startPumpSetup')
    return success()
    
@socket.on('stopPumpSetup')
def _socket_stopPumpSetup():
    bus.emit('barbot:stopPumpSetup')
    return success()

@socket.on('restart')
def _socket_restart():
    logger.info('Client requested restart')
    bus.emit('barbot:restart')
    return success()

@socket.on('shutdown')
def _socket_shutdown():
    logger.info('Client requested shutdown')
    bus.emit('barbot:shutdown')
    return success()

    
@bus.on('barbot:dispenserHold')
def _bus_dispenserHold(dispenserHold):
    socket.emit('dispenserHold', dispenserHold)
    
@bus.on('barbot:dispenserState')
def _bus_dispenserState(dispenserState):
    socket.emit('dispenserState', dispenserState)
    
@bus.on('barbot:pumpSetup')
def _bus_pumpSetup(pumpSetup):
    socket.emit('pumpSetup', pumpSetup)

@bus.on('barbot:drinkOrderStarted')
def _bus_drinkOrderStarted(o):
    socket.emit('dispensingDrinkOrder', o.to_dict(drink = True))
    
@bus.on('barbot:drinkOrderCompleted')
def _bus_drinkOrderCompleted(o):
    socket.emit('drinkOrderCompleted', o.to_dict(drink = True))
    
@bus.on('barbot:glassReady')
def _bus_glassReady(g):
    socket.emit('glassReady', g)
    

    