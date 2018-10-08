
import logging
from flask_socketio import emit
from peewee import IntegrityError, DoesNotExist

from ..bus import bus
from ..socket import socket, success, error
from ..db import ModelError
from ..models.Drink import Drink
from ..models.DrinkOrder import DrinkOrder


logger = logging.getLogger('Socket.DrinkOrders')

    
@socket.on('getDrinksMenu')
def _socket_getDrinksMenu():
    logger.info('getDrinksMenu')
    return success(items = [d.to_dict() for d in Drink.getMenuDrinks()])
    
@socket.on('getWaitingDrinkOrders')
def _socket_getWaitingDrinkOrders():
    logger.info('getWaitingDrinkOrders')
    return success(items = [do.to_dict(drink = True) for do in DrinkOrder.getWaiting()])

@socket.on('getDrinkOrder')
def _socket_getDrinkOrder(id):
    logger.info('getDrinkOrder')
    try:
        o = DrinkOrder.get(DrinkOrder.id == id)
        return success(item = o.to_dict(drink = True))
    except DoesNotExist:
        return error('Drink order not found!')
    
@bus.on('model:drinkOrder:saved')
def _bus_modelDrinkOrderSaved(o):
    socket.emit('drinkOrderSaved', o.to_dict(drink = True))

@bus.on('model:drinkOrder:deleted')
def _bus_modelDrinkOrderDeleted(o):
    socket.emit('drinkOrderDeleted', o.to_dict())

