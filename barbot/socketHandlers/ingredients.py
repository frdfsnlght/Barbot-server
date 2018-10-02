
import logging
from flask_socketio import emit
from peewee import IntegrityError, DoesNotExist

from ..bus import bus
from ..socket import socket, success, error
from ..db import ModelError
from ..models.Ingredient import Ingredient


logger = logging.getLogger('Socket.Ingredients')

@socket.on('getIngredients')
def _socket_getIngredients():
    logger.info('getIngredients')
    return { 'items': [i.to_dict() for i in Ingredient.select()] }

@socket.on('getIngredient')
def _socket_getIngredient(id):
    logger.info('getIngredient')
    try:
        i = Ingredient.get(Ingredient.id == id)
        return {'item': i.to_dict(drinks = True)}
    except DoesNotExist:
        return error('Ingredient not found!')
    
@socket.on('saveIngredient')
def _socket_saveIngredient(item):
    logger.info('saveIngredient')
    try:
        Ingredient.save_from_dict(item)
        return success()
    except IntegrityError:
        return error('That ingredient already exists!')
    except ModelError as e:
        return error(e.message)

@socket.on('deleteIngredient')
def _socket_deleteIngredient(id):
    logger.info('deleteIngredient')
    try:
        Ingredient.delete_by_id(id)
        return success()
    except DoesNotExist:
        return error('Ingredient not found!')

@bus.on('model:ingredient:saved')
def _bus_modelIngredientSaved(i):
    socket.emit('ingredientSaved', i.to_dict())

@bus.on('model:ingredient:deleted')
def _bus_modelIngredientDeleted(i):
    socket.emit('ingredientDeleted', i.to_dict())
        