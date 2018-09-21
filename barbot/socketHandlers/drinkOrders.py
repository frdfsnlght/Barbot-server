
from flask_socketio import emit
from peewee import IntegrityError
import logging

from barbot.socket import socket, success, error
from barbot.models import DrinkOrder


logger = logging.getLogger(__name__)

    
@socket.on('getDrinkOrders')
def socket_getDrinkOrders():
    logger.info('getDrinkOrders')
    return { 'items': [g.to_dict() for g in DrinkOrder.select()] }

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
    
    for k, v in item.items():
        setattr(do, k, v)
#    try:
    do.save()
#    except IntegrityError as e:
#        return error('???')
        
    emit('drinkOrderSaved', do.to_dict(), broadcast = True)
    
    return success()

@socket.on('deleteDrinkOrder')
def socket_deleteDrinkOrder(item):
    logger.info('deleteDrinkOrder')
    
    if 'id' in item.keys() and item['id'] != False:
        do = DrinkOrder.get(DrinkOrder.id == item['id'])
        if not do:
            return error('Drink order not found!')
        do.delete_instance()
        
        emit('drinkOrderDeleted', do.to_dict(), broadcast = True)
    
        return success()
    else:
        return error('Drink order not specified!')
 