
from flask_socketio import emit
from peewee import IntegrityError
import logging

from barbot.socket import socket, success, error
from barbot.models import DrinkOrder


logger = logging.getLogger(__name__)

    
@socket.on('getPendingDrinkOrders')
def socket_getPendingDrinkOrders():
    logger.info('getPendingDrinkOrders')
    return { 'items': [do.to_dict(drink = True) for do in DrinkOrder.select().where(DrinkOrder.startedDate == None)] }

@socket.on('getDrinkOrder')
def socket_getDrinkOrder(id):
    logger.info('getDrinkOrder')
    o = DrinkOrder.get(DrinkOrder.id == id)
    if not o:
        return error('Drink order not found!')
    return {'item': o.to_dict(drink = True)}
    
@socket.on('saveDrinkOrder')
def socket_saveDrinkOrder(item):
    logger.info('saveDrinkOrder')
    
    if 'id' in item.keys() and item['id'] != False:
        do = DrinkOrder.get(DrinkOrder.id == item['id'])
        if not do:
            return error('Drink order not found!')
        del item['id']
    else:
        do = DrinkOrder()
        
    if 'drink' in item.keys() and item['drink'] != False:
        d = Drink.get(Drink.id == item['drink'])
        if not d:
            return error('Drink not found!')
        item['drink'] = d
    
    do.set(item)
    do.save()
        
    emit('drinkOrderSaved', do.to_dict(drink = True), broadcast = True)
    
    return success()

@socket.on('deleteDrinkOrder')
def socket_deleteDrinkOrder(id):
    logger.info('deleteDrinkOrder')
    
    d = DrinkOrder.get(DrinkOrder.id == id)
    if not d:
        return error('Drink order not found!')
    d.delete_instance()
        
    emit('drinkOrderDeleted', do.to_dict(), broadcast = True)
    
    return success()
        
@socket.on('toggleDrinkOrderHold')
def socket_toggleDrinkOrderHold(id):
    logger.info('toggleDrinkOrderHold')
    
    d = DrinkOrder.get(DrinkOrder.id == id)
    if not d:
        return error('Drink order not found!')
    d.userHold = not d.userHold
    d.save()
        
    emit('drinkOrderSaved', d.to_dict(drink = True), broadcast = True)
    
    return success()
 