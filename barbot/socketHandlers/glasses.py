
from flask_socketio import emit
from peewee import IntegrityError
import logging

from barbot.socket import socket, success, error
from barbot.models import Glass


logger = logging.getLogger(__name__)

    
@socket.on('getGlasses')
def socket_getGlasses():
    logger.info('getGlasses')
    return { 'items': [g.to_dict() for g in Glass.select()] }

@socket.on('saveGlass')
def socket_saveGlass(item):
    logger.info('saveGlass')
    
    if 'id' in item.keys() and item['id'] != False:
        g = Glass.get(Glass.id == item['id'])
        if not g:
            return error('Glass not found!')
        del item['id']
    else:
        g = Glass()
        
    for k, v in item.items():
        setattr(g, k, v)
    try:
        g.save()
    except IntegrityError as e:
        return error('That glass already exists!')
        
    emit('glassSaved', g.to_dict(), broadcast = True)
    
    return success()

@socket.on('deleteGlass')
def socket_deleteGlass(item):
    logger.info('deleteGlass')
    
    if 'id' in item.keys() and item['id'] != False:
        g = Glass.get(Glass.id == item['id'])
        if not g:
            return error('Glass not found!')
        g.delete_instance()
        
        emit('glassDeleted', g.to_dict(), broadcast = True)
    
        return success()
    else:
        return error('Glass not specified!')
 