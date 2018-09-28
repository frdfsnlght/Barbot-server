
import logging, datetime, time
from threading import Thread, Event
from flask_socketio import emit

from barbot.events import bus
from barbot.socket import socket
from barbot.models import Drink, DrinkOrder, DrinkIngredient, Pump
from barbot.config import config
from barbot.db import db
import barbot.utils as utils


DISPENSE = 'dispense'
HOLD = 'hold'


logger = logging.getLogger('Barbot')
exitEvent = Event()
thread = None
state = DISPENSE
holdEvent = Event()
lastDrinkOrderCheckTime = time.time()


@bus.on('server:stop')
def _bus_serverStop():
    exitEvent.set()
    
@bus.on('client:connect')
def _bus_clientConnect():
    emit('barbotState', state)

@bus.on('server:start')
def _startThread():
    global thread
    exitEvent.clear()
    thread = Thread(target = _threadLoop, name = 'BarbotThread', daemon = True)
    thread.start()

def _threadLoop():
    global state
    logger.info('Barbot thread started')
    _changeState(DISPENSE)
    while not exitEvent.is_set():
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
    socket.emit('drinkOrderStarted', o.to_dict(drink = True))
    
    # TODO: dispense it
    time.sleep(5)
    
    
    o.completedDate = datetime.datetime.now()
    o.save()
    logger.info('Done dispensing "' + o.drink.name() + '" for ' + (o.name if o.name else 'unknown'))
    socket.emit('drinkOrderCompleted', o.to_dict(drink = True))
    
    DrinkOrder.deleteOldCompleted()
    
def _holdLoop():
    if not holdEvent.is_set(): # also require no pumps running, etc...
        _changeState(DISPENSE)
        return
    
    time.sleep(1)
    
    
@bus.on('server:start')
@db.atomic()
def _rebuildMenu():
    logger.info('rebuilding drinks menu')
    menuUpdated = False
    ingredients = Pump.getReadyIngredients()
    menuDrinks = Drink.getMenuDrinks()

#    print('Current menu:')
#    for drink in menuDrinks:
#        print(drink.name())
    
    # trivial case
    if not ingredients:
#        print('removing all drinks from the menu')
        for drink in menuDrinks:
            drink.isOnMenu = False
            drink.save()
            menuUpdated = True
        
    else:
#        print('-------------------------')
        for drink in Drink.getDrinksWithIngredients(ingredients):
#            print('--Considering ' + drink.name())
            
            # remove this drink from the existing menu drinks
            menuDrinks = [d for d in menuDrinks if d.id != drink.id]
            
            onMenu = True
            # check for all the drink's ingredients
            for di in drink.ingredients:
                pump = Pump.getPumpWithIngredientId(di.ingredient_id)
                if not pump or utils.toML(pump.amount, pump.units) < utils.toML(di.amount, di.units):
#                    print('drink "' + drink.name() + '" is missing ingredient ' + di.ingredient.name)
                    onMenu = False
                    break
            if onMenu != drink.isOnMenu:
#                print('changing isOnMenu to ' + str(onMenu))
                drink.isOnMenu = onMenu
                drink.save()
                menuUpdated = True
    
        # any drinks in the original list are no longer on the menu
        for drink in menuDrinks:
#            print('removing "' + drink.name() + '" from the menu')
            drink.isOnMenu = False
            drink.save()
            menuUpdated = True
            
    if menuUpdated:
        socket.emit('drinksMenuUpdated')
#        print('menu updated')
    
#    print('New menu:')
#    for drink in Drink.getMenuDrinks():
#        print(drink.name())
        
    _updateDrinkOrders()


@db.atomic()
def _updateDrinkOrders():
    logger.info('updating drink orders')
    readyPumps = Pump.getReadyPumps()
    for o in DrinkOrder.getWaiting():
        hold = False
        
        if o.drink.isOnMenu:
            # make sure there's enough of each ingredient
            for di in o.drink.ingredients:
                iPumps = [p for p in readyPumps if p.ingredient.id == di.ingredient.id]
                if not iPumps or utils.toML(iPumps[0].amount, iPumps[0].units) < utils.toML(di.amount, di.units):
                    hold = True
                    break
        else:
            hold = True
            
        if hold != o.ingredientHold:
            o.ingredientHold = hold
            o.save()
            socket.emit('drinkOrderSaved', o.to_dict(drink = True))

#        print(o.drink.name() + ': ' + str(o.ingredientHold))
            