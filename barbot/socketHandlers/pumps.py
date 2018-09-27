
from flask_socketio import emit
from peewee import IntegrityError
import logging

from barbot.socket import socket, success, error
from barbot.models import Pump
import barbot.pumps as pumps


logger = logging.getLogger('Socket_Pumps')

# TODO: most of this functionality should be moved to barbot.pumps with added states and checks

@socket.on('getPumps')
def socket_getPumps():
    logger.info('getPumps')
    return { 'items': [p.to_dict(ingredient = True) for p in pumps.pumps] }

@socket.on('getPump')
def socket_getPump(id):
    logger.info('getPump')
    p = Pump.get(Pump.id == id)
    if not p:
        return error('Pump not found!')
    return {'item': p.to_dict(ingredient = True)}
    
@socket.on('enablePump')
def socket_enablePump(id):
    logger.info('enablePump ' + str(id))
    p = Pump.get(Pump.id == id)
    if not p:
        return error('Pump not found!')
    if p.state == pumps.DISABLED:
        p.state = pumps.UNLOADED
        p.save()
        emit('pumpSaved', p.to_dict(), broadcast = True)
        return success()
    else:
        return error('Invalid pump state!')
    
@socket.on('disablePump')
def socket_disablePump(id):
    logger.info('disablePump ' + str(id))
    p = Pump.get(Pump.id == id)
    if not p:
        return error('Pump not found!')
    if p.state == pumps.UNLOADED:
        p.state = pumps.DISABLED
        p.save()
        emit('pumpSaved', p.to_dict(), broadcast = True)
        return success()
    else:
        return error('Invalid pump state!')

@socket.on('loadPump')
def socket_loadPump(opt):
    logger.info('loadPump ' + str(opt['id']))
    p = Pump.get(Pump.id == int(opt['id']))
    if not p:
        return error('Pump not found!')
    i = Ingredient.get(Ingredient.id == int(opt['ingredientId']))
    if not i:
        return error('Ingredient not found!')
    if p.state == pumps.UNLOADED:
        p.state = pumps.LOADED
        p.ingredient = i
        p.amount = float(opt['amount'])
        p.units = str(opt['units'])
        p.save()
        emit('pumpSaved', p.to_dict(ingredient = True), broadcast = True)
        return success()
    else:
        return error('Invalid pump state!')

@socket.on('unloadPump')
def socket_unloadPump(id):
    logger.info('unloadPump ' + str(id))
    p = Pump.get(Pump.id == id)
    if not p:
        return error('Pump not found!')
    if p.state == pumps.LOADED:
        p.state = pumps.UNLOADED
        p.ingredient = None
        p.amount = 0
        p.units = 'ml'
        p.save()
        emit('pumpSaved', p.to_dict(), broadcast = True)
        return success()
    else:
        return error('Invalid pump state!')
    

@socket.on('primePump')
def socket_primePump(opt):
    logger.info('primePump ' + str(opt['id']))
    p = Pump.get(Pump.id == int(opt['id']))
    if not p:
        return error('Pump not found!')
    
    if p.state == pumps.LOADED or p.state == pumps.READY:
        amount = float(opt['amount'])
        units = str(opt['units'])
        pumps.prime(p.id, amount, units)
        p.state = pumps.READY
        p.save()
        emit('pumpSaved', p.to_dict(ingredient = True), broadcast = True)
        return success()
    else:
        return error('Invalid pump state!')

@socket.on('reloadPump')
def socket_reloadPump(opt):
    logger.info('reloadPump ' + str(opt['id']))
    p = Pump.get(Pump.id == int(opt['id']))
    if not p:
        return error('Pump not found!')

    if p.state == pumps.READY or p.state == pumps.EMPTY:
        p.state = pumps.READY
        p.amount = float(opt['amount'])
        p.units = str(opt['units'])
        p.save()
        emit('pumpSaved', p.to_dict(ingredient = True), broadcast = True)
        return success()
    else:
        return error('Invalid pump state!')

@socket.on('drainPump')
def socket_drainPump(id):
    logger.info('drainPump ' + str(id))
    p = Pump.get(Pump.id == id)
    if not p:
        return error('Pump not found!')

    if p.state == pumps.READY or p.state == pumps.EMPTY:
        pumps.drain(id)
        p.state = pumps.DIRTY
        p.ingredient = None
        p.amount = 0
        p.units = 'ml'
        p.save()
        emit('pumpSaved', p.to_dict(ingredient = True), broadcast = True)
        return success()
    else:
        return error('Invalid pump state!')

@socket.on('cleanPump')
def socket_cleanPump(id):
    logger.info('cleanPump ' + str(id))
    p = Pump.get(Pump.id == id)
    if not p:
        return error('Pump not found!')

    if p.state == pumps.DIRTY:
        pumps.clean(id)
        p.state = pumps.UNLOADED
        p.save()
        emit('pumpSaved', p.to_dict(), broadcast = True)
        return success()
    else:
        return error('Invalid pump state!')

# TODO: stopPump - stops running pump no matter which state
