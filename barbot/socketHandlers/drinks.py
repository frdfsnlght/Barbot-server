
import logging
from flask_socketio import emit
from peewee import IntegrityError, DoesNotExist

from ..bus import bus
from ..socket import socket, success, error
from ..db import ModelError
from ..models.Drink import Drink


logger = logging.getLogger('Socket.Drinks')

    
@socket.on('getDrinks')
def _socket_getDrinks():
    logger.info('getDrinks')
    return { 'items': [d.to_dict(ingredients = True) for d in Drink.select()] }
    
@socket.on('getDrink')
def _socket_getDrink(id):
    logger.info('getDrink')
    try:
        d = Drink.get(Drink.id == id)
        return {'item': d.to_dict(glass = True, ingredients = True)}
    except DoesNotExist:
        return error('Drink not found!')
    
@socket.on('saveDrink')
def _socket_saveDrink(item):
    logger.info('saveDrink')
    try:
        Drink.save_from_dict(item)
        return success()
    except DoesNotExist:
        return error('Drink not found!')
    except IntegrityError:
        return error('That drink already exists!')
    except ModelError as e:
        return error(e)

@socket.on('deleteDrink')
def _socket_deleteDrink(id):
    logger.info('deleteDrink')
    try:
        Drink.delete_by_id(id)
        return success()
    except DoesNotExist:
        return error('Drink not found!')
         
@bus.on('model:drink:saved')
def _bus_modelDrinkSaved(d):
    socket.emit('drinkSaved', d.to_dict(glass = True, ingredients = True))

@bus.on('model:drink:deleted')
def _bus_modelDrinkDeleted(d):
    socket.emit('drinkDeleted', d.to_dict())

        
        
