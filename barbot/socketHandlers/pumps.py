
import logging
from flask_socketio import emit
from peewee import IntegrityError, DoesNotExist

from ..bus import bus
from ..socket import socket, success, error
from ..db import ModelError
from ..models.Pump import Pump

#import ..pumps as pumps


logger = logging.getLogger('Socket.Pumps')

# TODO: most of this functionality should be moved to barbot.pumps with added states and checks

@socket.on('getPumps')
def _socket_getPumps():
    logger.info('getPumps')
    return success(items = [p.to_dict(ingredient = True) for p in Pump.select()])
    
@socket.on('loadPump')
def _socket_loadPump(params):
    logger.info('loadPump ' + str(params['id']))
    try:
        Pump.loadPump(params)
        return success()
    except IntegrityError:
        return error('Ingredient is already loaded!')
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)

@socket.on('unloadPump')
def _socket_unloadPump(id):
    logger.info('unloadPump ' + str(id))
    try:
        Pump.unloadPump(id)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)
    
@socket.on('primePump')
def _socket_primePump(params):
    logger.info('primePump ' + str(params['id']))
    try:
        Pump.primePump(params, useThread = True)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)
    
@socket.on('drainPump')
def _socket_drainPump(id):
    logger.info('drainPump ' + str(id))
    try:
        Pump.drainPump(id, useThread = True)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)

@socket.on('cleanPump')
def socket_cleanPump(params):
    logger.info('cleanPump ' + str(params['id']))
    try:
        Pump.cleanPump(params, useThread = True)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)

# TODO: stopPump - stops running pump no matter which state


@bus.on('model:pump:saved')
def _bus_modelPumpSaved(p):
    socket.emit('pumpSaved', p.to_dict(ingredient = True))
