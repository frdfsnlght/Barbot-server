
import logging, datetime, time
from threading import Thread, Event
#from flask_socketio import emit

import barbot.events as events
from barbot.socket import socket
from barbot.models import DrinkOrder
from barbot.config import config

DISPENSE = 'dispense'
HOLD = 'hold'


logger = logging.getLogger('Barbot')
thread = None
state = DISPENSE
holdEvent = Event()
lastDrinkOrderCheckTime = time.time()


def startThread():
    global thread
    thread = Thread(target = _threadLoop, name = 'BarbotThread')
    thread.daemon = True
    thread.start()

def _threadLoop():
    global state
    logger.info('Barbot thread started')
    _changeState(DISPENSE)
    while not events.exitEvent.is_set():
        if state == DISPENSE:
            _dispenseLoop()
        elif state == HOLD:
            _holdLoop()
        else:
            logger.error('Unexpected state: ' + state)
            state = DISPENSE
        
    logger.info('Barbot thread stopped')

def _changeState(newState):
    global state
    state = newState
    try:
        socket.emit('barbotState', state)
    except:
        # ignore
        pass
    logger.info('Entering ' + state + ' state')
    
def _dispenseLoop():
    global lastDrinkOrderCheckTime
    if holdEvent.is_set():
        _changeState(HOLD)
        return

    if (time.time() - lastDrinkOrderCheckTime) > 5:
        lastDrinkOrderCheckTime = time.time()
        o = DrinkOrder.getFirstPending()
        if o:
            _dispenseDrinkOrder(o)
    else:
        time.sleep(1)
        
    
    time.sleep(1)
    
def _dispenseDrinkOrder(o):
    o.startedDate = datetime.datetime.now()
    o.save()
    logger.info('Dispensing "' + o.drink.name() + '" for ' + (o.name if o.name else 'unknown'))
    socket.emit('drinkOrderSaved', o.to_dict(drink = True))
    
    # TODO: dispense it
    time.sleep(5)
    
    
    o.completedDate = datetime.datetime.now()
    o.save()
    logger.info('Done dispensing "' + o.drink.name() + '" for ' + (o.name if o.name else 'unknown'))
    socket.emit('drinkOrderSaved', o.to_dict(drink = True))
    
    DrinkOrder.deleteOldCompleted()
    
def _holdLoop():
    if not holdEvent.is_set(): # also require no pumps running, etc...
        _changeState(DISPENSE)
        return
    
    time.sleep(1)
    