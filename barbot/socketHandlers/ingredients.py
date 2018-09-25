
from flask_socketio import emit
from peewee import IntegrityError
import logging

from barbot.socket import socket, success, error
from barbot.models import Ingredient


logger = logging.getLogger(__name__)

@socket.on('getIngredients')
def socket_getIngredients():
    logger.info('getIngredients')
    return { 'items': [i.to_dict() for i in Ingredient.select()] }

@socket.on('getIngredient')
def socket_getIngredient(id):
    logger.info('getIngredient')
    i = Ingredient.get(Ingredient.id == id)
    if not i:
        return error('Ingredient not found!')
    return i.to_dict(drinks = True)
    
@socket.on('saveIngredient')
def socket_saveIngredient(item):
    logger.info('saveIngredient')
    
    if 'id' in item.keys() and item['id'] != False:
        i = Ingredient.get(Ingredient.id == item['id'])
        if not i:
            return error('Ingredient not found!')
        del item['id']
    else:
        i = Ingredient()
    
    i.set(item)
    try:
        i.save()
    except IntegrityError as e:
        return error('That ingredient already exists!')
        
    emit('ingredientSaved', i.to_dict(), broadcast = True)
    
    return success()

@socket.on('deleteIngredient')
def socket_deleteIngredient(item):
    logger.info('deleteIngredient')
    
    if 'id' in item.keys() and item['id'] != False:
        i = Ingredient.get(Ingredient.id == item['id'])
        if not i:
            return error('Ingredient not found!')
        i.delete_instance()
        
        emit('ingredientDeleted', i.to_dict(), broadcast = True)
    
        return success()
    else:
        return error('Ingredient not specified!')
 