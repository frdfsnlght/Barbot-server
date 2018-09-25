
import logging, datetime
from flask_socketio import emit
from peewee import IntegrityError

from barbot.socket import socket, success, error
from barbot.models import Drink, DrinkIngredient
from barbot.db import db

logger = logging.getLogger(__name__)

    
@socket.on('getDrinks')
def socket_getDrinks():
    logger.info('getDrinks')
    return { 'items': [d.to_dict(ingredients = True) for d in Drink.select()] }
    
@socket.on('getDrink')
def socket_getDrink(id):
    logger.info('getDrink')
    d = Drink.get(Drink.id == id)
    if not d:
        return error('Drink not found!')
    return d.to_dict(glass = True, ingredients = True)
    
@socket.on('saveDrink')
@db.atomic()
def socket_saveDrink(item):
    logger.info('saveDrink')
    logger.info(item)
    
    if 'id' in item.keys() and item['id'] != False:
        d = Drink.get(Drink.id == item['id'])
        if not d:
            return error('Drink not found!')
        del item['id']
    else:
        d = Drink()
    
    d.set(item)
    d.updatedDate = datetime.datetime.now()
    
    try:
        d.save()
    except IntegrityError as e:
        return error('That drink already exists!')

    # handle ingredients
    if 'ingredients' in item:
        d.setIngredients(item['ingredients'])
        
    emit('drinkSaved', d.to_dict(ingredients = True), broadcast = True)
    
    return success()

@socket.on('deleteDrink')
def socket_deleteDrink(item):
    logger.info('deleteDrink')
    
    if 'id' in item.keys() and item['id'] != False:
        d = Drink.get(Drink.id == item['id'])
        if not d:
            return error('Drink not found!')
        d.delete_instance()
        
        emit('drinkDeleted', d.to_dict(), broadcast = True)
    
        return success()
    else:
        return error('Drink not specified!')
 