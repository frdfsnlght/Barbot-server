
import logging
from flask_socketio import emit
from peewee import IntegrityError, DoesNotExist

from ..bus import bus
from ..socket import socket, success, error
from ..db import ModelError
from ..models.Glass import Glass


logger = logging.getLogger('Socket.Glasses')

    
@socket.on('getGlasses')
def _socket_getGlasses():
    logger.info('getGlasses')
    return success(items = [g.to_dict() for g in Glass.select()])

@socket.on('getGlass')
def _socket_getGlass(id):
    logger.info('getGlass')
    try:
        g = Glass.get(Glass.id == id)
        return success(item = g.to_dict(drinks = True))
    except DoesNotExist:
        return error('Glass not found!')
    
@socket.on('saveGlass')
def _socket_saveGlass(item):
    logger.info('saveGlass')
    try:
        Glass.save_from_dict(item)
        return success()
    except IntegrityError:
        return error('That glass already exists!')
    except ModelError as e:
        return error(e)

@socket.on('deleteGlass')
def _socket_deleteGlass(id):
    logger.info('deleteGlass')
    try:
        Glass.delete_by_id(id)
        return success()
    except DoesNotExist:
        return error('Drink not found!')
         
@bus.on('model:glass:saved')
def _bus_modelGlassSaved(g):
    socket.emit('glassSaved', g.to_dict())

@bus.on('model:glass:deleted')
def _bus_modelGlassDeleted(g):
    socket.emit('glassDeleted', g.to_dict())
