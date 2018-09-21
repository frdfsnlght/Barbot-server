
import sys, os, time, logging
from threading import Thread
from flask_socketio import emit

import barbot.config as config
import barbot.events as events
from barbot.socket import socket

logger = logging.getLogger(__name__)
thread = None
state = 'n/a'


def startThread():
    global thread
    if not config.config.getint('wifi', 'checkInterval'):
        logging.info('Wifi checking disabled')
        return
    thread = Thread(target = _threadLoop, name = 'WifiThread')
    thread.daemon = True
    thread.start()

def _threadLoop():
    logger.info('Wifi thread started')
    time.sleep(3)
    while not events.exitEvent.is_set():
        _checkState()
        events.exitEvent.wait(config.config.getint('wifi', 'checkInterval'))
    logger.info('Wifi thread stopped')
    

def _checkState():
    global state
    return
    
    if state == 'n/a':
        state = 'n/c'
    elif state == 'n/c':
        state = 0
    elif state == 4:
        state = 'n/a'
    else:
        state = state + 1
        
    logger.info('check ' + str(state))

    socket.emit('wifiState', state)  # broadcast by default
    
def emitState():
    emit('wifiState', state)
    