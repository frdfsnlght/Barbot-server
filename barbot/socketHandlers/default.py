
import logging
from flask import request, session
from flask_socketio import emit
from peewee import DoesNotExist

from ..config import config
from ..socket import socket, success, error, checkAdmin
from ..bus import bus
from ..db import ModelError
from ..models.User import User


logger = logging.getLogger('Socket.Default')


@socket.on_error_default  # handles all namespaces without an explicit error handler
def _socket_default_error_handler(e):
    logger.exception(e)
    return error('An internal error has ocurred!')

#================================================================
# socket events
#
    
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
    item['sessionId'] = request.sid
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

@socket.on('dispenseControl')
def _socket_dispenseControl(ctl):
    bus.emit('barbot:dispenseControl', ctl)
    return success()
    
    
#================================================================
# bus events
#
    
@bus.on('barbot:dispenserHold')
def _bus_dispenserHold(dispenserHold, singleClient = False):
    if singleClient:
        emit('dispenserHold', dispenserHold)
    else:
        socket.emit('dispenserHold', dispenserHold)
    
@bus.on('barbot:dispenseState')
def _bus_dispenseState(dispenseState, dispenseDrinkOrder, singleClient = False):
    if dispenseDrinkOrder:
        dispenseDrinkOrder = dispenseDrinkOrder.to_dict(drink = True, glass = True)
    if singleClient:
        emit('dispenseState', {'state': dispenseState, 'order': dispenseDrinkOrder})
    else:
        socket.emit('dispenseState', {'state': dispenseState, 'order': dispenseDrinkOrder})
    
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

