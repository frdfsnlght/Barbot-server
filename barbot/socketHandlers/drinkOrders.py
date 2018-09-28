
from flask_socketio import emit
from peewee import IntegrityError
import logging

from barbot.socket import socket, success, error
from barbot.models import Drink, DrinkOrder


logger = logging.getLogger('Socket_DrinkOrders')

    
@socket.on('getDrinksMenu')
def socket_getDrinksMenu():
    logger.info('getDrinksMenu')
    return { 'items': [d.to_dict() for d in Drink.getMenuDrinks()] }
    
@socket.on('getWaitingDrinkOrders')
def socket_getWaitingDrinkOrders():
    logger.info('getWaitingDrinkOrders')
    return { 'items': [do.to_dict(drink = True) for do in DrinkOrder.getWaiting()] }

@socket.on('getDrinkOrder')
def socket_getDrinkOrder(id):
    logger.info('getDrinkOrder')
    o = DrinkOrder.get_or_none(DrinkOrder.id == id)
    if not o:
        return error('Drink order not found!')
    return {'item': o.to_dict(drink = True)}
    
@socket.on('submitDrinkOrder')
def socket_submitDrinkOrder(item):
    logger.info('submitDrinkOrder')
    
    do = DrinkOrder()
    d = Drink.get_or_none(Drink.id == item['drinkId'])
    if not d:
        return error('Drink not found!')
    item['drink'] = d
    
    do.set(item)
    do.save()
        
    emit('drinkOrderSubmitted', do.to_dict(drink = True), broadcast = True)
    
    return success()

@socket.on('cancelDrinkOrder')
def socket_cancelDrinkOrder(id):
    logger.info('cancelDrinkOrder')
    
    d = DrinkOrder.get_or_none(DrinkOrder.id == id, DrinkOrder.startedDate.is_null())
    if not d:
        return error('Drink order not found!')
    d.delete_instance()
        
    emit('drinkOrderCancelled', do.to_dict(), broadcast = True)
    
    return success()
        
@socket.on('toggleDrinkOrderHold')
def socket_toggleDrinkOrderHold(id):
    logger.info('toggleDrinkOrderHold')
    
    d = DrinkOrder.get_or_none(DrinkOrder.id == id, DrinkOrder.startedDate.is_null())
    if not d:
        return error('Drink order not found!')
    d.userHold = not d.userHold
    d.save()
        
    emit('drinkOrderUpdated', d.to_dict(drink = True), broadcast = True)
    
    return success()
 