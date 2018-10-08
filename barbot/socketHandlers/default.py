
import logging, re
from flask import request, session
from flask_socketio import emit
from peewee import DoesNotExist

from ..config import config
from ..socket import socket, success, error, checkAdmin
from ..bus import bus
from ..db import ModelError
from ..models.User import User


booleanPattern = re.compile(r"(i?)(true|false|yes|no)")
intPattern = re.compile(r"-?\d+")
floatPattern = re.compile(r"-?\d*\.\d+")

logger = logging.getLogger('Socket.Default')


@socket.on_error_default  # handles all namespaces without an explicit error handler
def _socket_default_error_handler(e):
    logger.exception(e)
    return error('An internal error has ocurred!')

#================================================================
# socket events
#
    
@socket.on('connect')
def _socket_connect():
    logger.info('Connection opened from ' + request.remote_addr)
    emit('clientOptions', getClientOptions())
    bus.emit('client:connect')

@socket.on('disconnect')
def _socket_disconnect():
    logger.info('Connection closed from ' + request.remote_addr)
    bus.emit('client:disconnect')

@socket.on('login')
def _socket_login(params):
    user = User.authenticate(params['name'], params['password'])
    if not user:
        return error('Login failed')
    else:
        session['user'] = user
        return success(user = user.to_dict())
        
@socket.on('logout')
def _socket_logout():
    if 'user' in session:
        del session['user']
    return success()

@socket.on('toggleDispenserHold')
def _socket_toggleDispenserHold():
    bus.emit('barbot:toggleDispenserHold')
    return success()

@socket.on('startPumpSetup')
def _socket_startPumpSetup():
    if not checkAdmin('pumpSetupRequiresAdmin'):
        return error('Permission denied!')
    bus.emit('barbot:startPumpSetup')
    return success()
    
@socket.on('stopPumpSetup')
def _socket_stopPumpSetup():
    bus.emit('barbot:stopPumpSetup')
    return success()

@socket.on('restart')
def _socket_restart():
    if not checkAdmin('restartRequiresAdmin'):
        return error('Permission denied!')
    logger.info('Client requested restart')
    bus.emit('barbot:restart')
    return success()

@socket.on('shutdown')
def _socket_shutdown():
    if not checkAdmin('shutdownRequiresAdmin'):
        return error('Permission denied!')
    logger.info('Client requested shutdown')
    bus.emit('barbot:shutdown')
    return success()

@socket.on('setParentalLock')
def _socket_setParentalLock(code):
    logger.info('setParentalLock')
    bus.emit('barbot:setParentalLock', code)
    return success()
        
@socket.on('submitDrinkOrder')
def _socket_submitDrinkOrder(item):
    logger.info('submitDrinkOrder')
    try:
        bus.emit('barbot:submitDrinkOrder', item)
        return success()
    except DoesNotExist:
        return error('Drink not found!')
    except ModelError as e:
        return error(e)

@socket.on('cancelDrinkOrder')
def _socket_cancelDrinkOrder(id):
    logger.info('cancelDrinkOrder')
    try:
        bus.emit('barbot:cancelDrinkOrder', id)
        return success()
    except DoesNotExist:
        return error('Drink order not found!')
        
@socket.on('toggleDrinkOrderHold')
def _socket_toggleDrinkOrderHold(id):
    logger.info('toggleDrinkOrderHold')
    try:
        bus.emit('barbot:toggleDrinkOrderHold', id)
        return success()
    except DoesNotExist:
        return error('Drink order not found!')


#================================================================
# bus events
#
    
@bus.on('barbot:dispenserHold')
def _bus_dispenserHold(dispenserHold, singleClient = False):
    if singleClient:
        emit('dispenserHold', dispenserHold)
    else:
        socket.emit('dispenserHold', dispenserHold)
    
@bus.on('barbot:dispenserState')
def _bus_dispenserState(dispenserState, singleClient = False):
    if singleClient:
        emit('dispenserState', dispenserState)
    else:
        socket.emit('dispenserState', dispenserState)
    
@bus.on('barbot:pumpSetup')
def _bus_pumpSetup(pumpSetup, singleClient = False):
    if singleClient:
        emit('pumpSetup', pumpSetup)
    else:
        socket.emit('pumpSetup', pumpSetup)

@bus.on('barbot:glassReady')
def _bus_glassReady(g, singleClient = False):
    if singleClient:
        emit('glassReady', g)
    else:
        socket.emit('glassReady', g)
    
@bus.on('barbot:parentalLock')
def _bus_parentalLock(locked, singleClient = False):
    if singleClient:
        emit('parentalLock', locked)
    else:
        socket.emit('parentalLock', locked)

@bus.on('barbot:drinkOrderStarted')
def _bus_drinkOrderStarted(o):
    socket.emit('dispensingDrinkOrder', o.to_dict(drink = True))
    
@bus.on('barbot:drinkOrderCompleted')
def _bus_drinkOrderCompleted(o):
    socket.emit('drinkOrderCompleted', o.to_dict(drink = True))
    
@bus.on('config:reloaded')
def _but_configReloaded():
    socket.emit('clientOptions', getClientOptions())

    
    
def getClientOptions():
    opts = dict(config.items('client'))
    for k, v in opts.items():
        if booleanPattern.match(v):
            opts[k] = config.getboolean('client', k)
        elif intPattern.match(v):
            opts[k] = config.getint('client', k)
        elif floatPattern.match(v):
            opts[k] = config.getfloat('client', k)
    return opts
