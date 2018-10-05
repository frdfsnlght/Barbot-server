
import logging, datetime, time, subprocess
from threading import Thread, Event

from .bus import bus
from .config import config
from .db import db
from . import utils
from .models.Drink import Drink
from .models.DrinkOrder import DrinkOrder
from .models.DrinkIngredient import DrinkIngredient
from .models.Pump import Pump


IDLE = 'idle'
WAITING_FOR_GLASS = 'waiting for glass'
DISPENSING = 'dispensing'

# TODO: add control for e-stop

logger = logging.getLogger('Barbot')
exitEvent = Event()
thread = None
dispenserHold = False
dispenserState = IDLE
pumpSetup = False
glassReady = False
requestPumpSetup = False
suppressMenuRebuild = False

lastDrinkOrderCheckTime = time.time()


#-----------------
# TODO: remove this temp code someday
glassThread = None
import os.path
from . import paths
@bus.on('server:start')
def _bus_startGlassThread():
    global glassThread
    glassThread = Thread(target = _glassThreadLoop, name = 'BarbotGlassThread', daemon = True)
    glassThread.start()
def _glassThreadLoop():
    global glassReady
    while not exitEvent.is_set():
        newGlassReady = os.path.isfile(os.path.join(paths.VAR_DIR, 'glass'))
        if newGlassReady != glassReady:
            glassReady = newGlassReady
            bus.emit('barbot:glassReady', glassReady)
        time.sleep(1)
# end of temp code
#---------------------

@bus.on('server:stop')
def _bus_serverStop():
    exitEvent.set()
    
@bus.on('client:connect')
def _bus_clientConnect():
    bus.emit('barbot:dispenserHold', dispenserHold)
    bus.emit('barbot:dispenserState', dispenserState)
    bus.emit('barbot:pumpSetup', pumpSetup)
    bus.emit('barbot:glassReady', glassReady)

@bus.on('server:start')
def _bus_startThread():
    global thread
    exitEvent.clear()
    thread = Thread(target = _threadLoop, name = 'BarbotThread', daemon = True)
    thread.start()

@bus.on('barbot:restart')
def _bus_restart():
    cmd = config.get('server', 'restartCommand').split(' ')
    out = subprocess.run(cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True)
    if out.returncode != 0:
        logger.error('Error trying to restart: {}'.format(out.stdout))
        
@bus.on('barbot:shutdown')
def _bus_shutdown():
    cmd = config.get('server', 'shutdownCommand').split(' ')
    out = subprocess.run(cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True)
    if out.returncode != 0:
        logger.error('Error trying to shutdown: {}'.format(out.stdout))
    
@bus.on('barbot:toggleDispenserHold')
def _bus_toggleDispenserHold():
    global dispenserHold
    dispenserHold = not dispenserHold
    bus.emit('barbot:dispenserHold', dispenserHold)
    
@bus.on('barbot:startPumpSetup')
def _bus_startPumpSetup():
    global requestPumpSetup
    requestPumpSetup = True
    
@bus.on('barbot:stopPumpSetup')
def _bus_stopPumpSetup():
    global requestPumpSetup, pumpSetup
    requestPumpSetup = False
    pumpSetup = False
    bus.emit('barbot:pumpSetup', pumpSetup)

def _threadLoop():
    global lastDrinkOrderCheckTime, requestPumpSetup, pumpSetup
    logger.info('Barbot thread started')
#    _changeState(DISPENSE)
    while not exitEvent.is_set():
        if requestPumpSetup:
            requestPumpSetup = False
            pumpSetup = True
            bus.emit('barbot:pumpSetup', pumpSetup)
            
        # TODO: ensure pumps are stopped too!
        while pumpSetup or dispenserHold:
            time.sleep(1)
            
        if (time.time() - lastDrinkOrderCheckTime) > 5:
            lastDrinkOrderCheckTime = time.time()
            o = DrinkOrder.getFirstPending()
            if o:
                _dispenseDrinkOrder(o)
                time.sleep(1)
        else:
            time.sleep(1)
            
    logger.info('Barbot thread stopped')
    
def _dispenseDrinkOrder(o):
    global dispenserState, dispensingDrinkOrder
    o.startedDate = datetime.datetime.now()
    o.save()
    dispenserState = WAITING_FOR_GLASS
    dispensingDrinkOrder = o
    logger.info('Dispensing "{}" for {}'.format(o.drink.name(), o.name if o.name else 'unknown'))
    bus.emit('barbot:drinkOrderStarted', dispensingDrinkOrder)
    bus.emit('barbot:dispenserState', dispenserState)
    
    # TODO: wait for glass
    time.sleep(3)

    dispenserState = DISPENSING
    bus.emit('barbot:dispenserState', dispenserState)
    
    # TODO: dispense it
    time.sleep(5)
    
    o.completedDate = datetime.datetime.now()
    o.save()
    dispenserState = IDLE
    logger.info('Done dispensing "{}" for {}'.format(o.drink.name(), o.name if o.name else 'unknown'))
    bus.emit('barbot:drinkOrderCompleted', dispensingDrinkOrder)
    bus.emit('barbot:dispenserState', dispenserState)
    _rebuildMenu()
    
    DrinkOrder.deleteOldCompleted()

@bus.on('model:pump:stateChanged')
def _bus_pumpChanged(pump, previousState):
    if pump.state == Pump.READY or previousState == Pump.READY:
        _rebuildMenu()

@bus.on('model:drink:saved')
def _bus_drinkSaved(drink):
    if not suppressMenuRebuild:
        _rebuildMenu()

@bus.on('model:drink:deleted')
def _bus_drinkDeleted(drink):
    _rebuildMenu()

@bus.on('server:start')
@db.atomic()
def _rebuildMenu():
    global suppressMenuRebuild
    logger.info('Rebuilding drinks menu')
    suppressMenuRebuild = True
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
                if not pump or pump.state == Pump.EMPTY or utils.toML(pump.amount, pump.units) < utils.toML(di.amount, di.units):
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
            
#    if menuUpdated:
    bus.emit('barbot:drinksMenuUpdated')
#        print('menu updated')
    
#    print('New menu:')
#    for drink in Drink.getMenuDrinks():
#        print(drink.name())
        
    _updateDrinkOrders()
    suppressMenuRebuild = False

@db.atomic()
def _updateDrinkOrders():
    logger.info('Updating drink orders')
    readyPumps = Pump.getReadyPumps()
    for o in DrinkOrder.getWaiting():
        if o.drink.isOnMenu == o.ingredientHold:
            o.ingredientHold = not o.drink.isOnMenu
            o.save()
            