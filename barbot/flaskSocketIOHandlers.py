
from flask import request
from flask_socketio import send, emit
from peewee import IntegrityError
import logging
import json

from barbot.flaskSocketIO import socket
from barbot.models import Glass

logger = logging.getLogger(__name__)


class MessageError(Exception):
    pass
    
    
@socket.on('connect')
def sock_connect():
    logger.info('socketio connection opened from ' + request.remote_addr)

@socket.on('disconnect')
def sock_disconnect():
    logger.info('socketio connection closed from ' + request.remote_addr)

@socket.on_error_default  # handles all namespaces without an explicit error handler
def default_error_handler(e):
    if not isinstance(e, MessageError):
        logger.exception(e)
    return {
        'error': e.message
    }
    
    
#@sock.on('message')
#def sock_message(message):
#    logger.info('received message: ' + message)
#    return 'ack'
    
#@sock.on('test-event')
#def sock_test_event(data):
#    logger.info('received test-event: ' + json.dumps(data))
#    emit('test-event-response', data)
    
@socket.on('getGlasses')
def sock_getGlasses():
    logger.info('getGlasses')
    return { 'items': [g.to_dict() for g in Glass.select()] }

@socket.on('saveGlass')
def sock_saveGlass(item):
    logger.info('saveGlass')
    logger.info(item)
    
    if 'id' in item.keys() and item['id'] != False:
        g = Glass.get(Glass.id == item['id'])
        if not g:
            raise MessageError('Glass not found!')
        del item['id']
    else:
        g = Glass()
        
    for k, v in item.items():
        setattr(g, k, v)
    try:
        g.save()
    except IntegrityError:
        raise MessageError('That glass already exists!')
        
    emit('glassSaved', g.to_dict(), broadcast = True)
    
    return {'error': False}

@socket.on('deleteGlass')
def sock_deleteGlass(item):
    logger.info('deleteGlass')
    logger.info(item)
    
    if 'id' in item.keys() and item['id'] != False:
        g = Glass.get(Glass.id == item['id'])
        if not g:
            raise MessageError('Glass not found!')
        g.delete_instance()
        
        emit('glassDeleted', g.to_dict(), broadcast = True)
    
        return {'error': False}
    else:
        raise MessageError('Glass not specified!')


    