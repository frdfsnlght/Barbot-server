
import logging, datetime, time, subprocess, re
from threading import Thread, Event

from .bus import bus
from .config import config
from .db import db, ModelError
from . import serial
from . import utils
from .models.Drink import Drink
from .models.DrinkOrder import DrinkOrder
from .models.DrinkIngredient import DrinkIngredient
from .models.Pump import Pump, anyPumpsRunning

    
ST_START = 'start'
ST_DISPENSE = 'dispense'
ST_PICKUP = 'pickup'
ST_GLASS_CLEAR = 'glassClear'
ST_CANCEL_CLEAR = 'cancelClear'

CTL_START = 'start'
CTL_CANCEL = 'cancel'
CTL_OK = 'ok'


sensorEventPattern = re.compile(r"(?i)S(\d)")

# TODO: add control for e-stop?

logger = logging.getLogger('Barbot')
exitEvent = Event()
thread = None
dispenserHold = False
pumpSetup = False
glassReady = False
requestPumpSetup = False
suppressMenuRebuild = False

dispenseState = None
dispenseControl = None
dispenseDrinkOrder = None
dispenseEvent = Event()

lastDrinkOrderCheckTime = time.time()


@bus.on('server:start')
def _bus_serverStart():
    global thread
    exitEvent.clear()
    thread = Thread(target = _threadLoop, name = 'BarbotThread', daemon = True)
    thread.start()

@bus.on('server:stop')
def _bus_serverStop():
    exitEvent.set()
    
@bus.on('client:connect')
def _bus_clientConnect():
    bus.emit('barbot:dispenserHold', dispenserHold, singleClient = True)
    bus.emit('barbot:pumpSetup', pumpSetup, singleClient = True)
    bus.emit('barbot:glassReady', glassReady, singleClient = True)
    bus.emit('barbot:parentalLock', True if _getParentalCode() else False, singleClient = True)
    bus.emit('barbot:dispenseState', dispenseState, dispenseDrinkOrder, singleClient = True)

@bus.on('serial:event')
def _bus_serialEvent(e):
    global glassReady
    m = sensorEventPattern.match(e)
    if m:
        newGlassReady = m.group(1) == '1'
        if newGlassReady != glassReady:
            glassReady = newGlassReady
            bus.emit('barbot:glassReady', glassReady)
            dispenseEvent.set()
            
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
            dispenseEvent.set()
        time.sleep(1)
# end of temp code
#---------------------

@bus.on('barbot:restart')
def _bus_restart():
    # TODO: set lights
    
    cmd = config.get('server', 'restartCommand').split(' ')
    out = subprocess.run(cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True)
    if out.returncode != 0:
        logger.error('Error trying to restart: {}'.format(out.stdout))
        
@bus.on('barbot:shutdown')
def _bus_shutdown():
    # TODO: set lights
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
    _rebuildMenu()
    bus.emit('barbot:pumpSetup', pumpSetup)

@bus.on('barbot:setParentalLock')
def _bus_setParentalLock(code):
    if not code:
        try:
            os.remove(config.getpath('barbot', 'parentalCodeFile'))
        except IOError:
            pass
    else:
        open(config.getpath('barbot', 'parentalCodeFile'), 'w').write(code)
    bus.emit('barbot:parentalLock', True if code else False)

def _getParentalCode():
    try:
        return open(config.getpath('barbot', 'parentalCodeFile')).read().rstrip()
    except IOError:
        return False

@bus.on('barbot:submitDrinkOrder')
def _bus_submitDrinkOrder(item):
    d = Drink.get(Drink.id == item['drinkId'])
    if d.isAlcoholic:
        code = _getParentalCode()
        if code:
            if not 'parentalCode' in item:
                raise ModelError('Parental code required!')
            if item['parentalCode'] != code:
                raise ModelError('Invalid parental code!')
    o = DrinkOrder.submitFromDict(item)
    bus.emit('barbot:drinkOrderSubmitted', o)

@bus.on('barbot:cancelDrinkOrder')
def _bus_cancelDrinkOrder(id):
    o = DrinkOrder.cancelById(id)
    bus.emit('barbot:drinkOrderCancelled', o)
        
@bus.on('barbot:toggleDrinkOrderHold')
def _bus_toggleDrinkOrderHold(id):
    o = DrinkOrder.toggleHoldById(id)
    bus.emit('barbot:drinkOrderHoldToggled', o)
       
@bus.on('barbot:dispenseControl')
def _bus_dispenseControl(ctl):
    global dispenseControl
    dispenseControl = ctl
    dispenseEvent.set()
        
def _threadLoop():
    global lastDrinkOrderCheckTime, requestPumpSetup, pumpSetup
    logger.info('Barbot thread started')
    while not exitEvent.is_set():
        if requestPumpSetup:
            requestPumpSetup = False
            pumpSetup = True
            bus.emit('barbot:pumpSetup', pumpSetup)
            
        while pumpSetup or dispenserHold or anyPumpsRunning():
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
    global dispenseState, dispenseDrinkOrder, dispenseControl
    # this gets the drink out of the queue
    o.startedDate = datetime.datetime.now()
    o.save()
    
    dispenseDrinkOrder = o
    logger.info('Preparing to dispense {}'.format(dispenseDrinkOrder.desc()))
    
    # wait for user to start or cancel the order
    
    dispenseState = ST_START
    dispenseEvent.clear()
    dispenseControl = None
    bus.emit('barbot:dispenseState', dispenseState, dispenseDrinkOrder)
    
    # TODO: set lights, play clip
    
    while True:
        dispenseEvent.wait()
        dispenseEvent.clear()
        # glassReady or dispenseControl changed
        
        if dispenseControl == CTL_CANCEL:
            logger.info('Cancelled dispensing {}'.format(dispenseDrinkOrder.desc()))
            dispenseDrinkOrder.place_on_hold()
            dispenseDrinkOrder = None
            dispenseState = None
            bus.emit('barbot:dispenseState', dispenseState, dispenseDrinkOrder)
            return
        
        if dispenseControl == CTL_START and glassReady:
            dispenseState = ST_DISPENSE
            bus.emit('barbot:dispenseState', dispenseState, dispenseDrinkOrder)
            logger.info('Starting to dispense {}'.format(dispenseDrinkOrder.desc()))
            break
    
    drink = dispenseDrinkOrder.drink
    dispenseControl = None
    
    for step in sorted({i.step for i in drink.ingredients}):
    
        ingredients = [di for di in drink.ingredients if di.step == step]
        logger.info('Executing step {}, {} ingredients'.format(step, len(ingredients)))
        pumps = []
        
        # start the pumps
        for di in ingredients:
            ingredient = di.ingredient
            pump = ingredient.pump.first()
            amount = utils.toML(di.amount, di.units)
            pump.forward(amount)
            ingredient.timesDispensed = ingredient.timesDispensed + 1
            ingredient.amountDispensed = ingredient.amountDispensed + amount
            ingredient.save()
            pumps.append(pump)
            
        # wait for the pumps to stop, glass removed, order cancelled
        
        while True and dispenseState == ST_DISPENSE:
            if not pumps[-1].running:
                pumps.pop()
            if not len(pumps):
                # all pumps have stopped
                break

            if dispenseEvent.wait(0.1):
                dispenseEvent.clear()
                
                if not glassReady:
                    logger.warning('Glass removed while dispensing {}'.format(dispenseDrinkOrder.desc()))
                    for pump in pumps:
                        pump.stop()
                    dispenseDrinkOrder.place_on_hold()
                    dispenseDrinkOrder = None
                    dispenseState = ST_GLASS_CLEAR
                    # TODO: set lights

                if dispenseControl == CTL_CANCEL:
                    logger.info('Cancelled dispensing {}'.format(dispenseDrinkOrder.desc()))
                    for pump in pumps:
                        pump.stop()
                    dispenseDrinkOrder.place_on_hold()
                    dispenseDrinkOrder = None
                    dispenseState = ST_CANCEL_CLEAR
                    # TODO: set lights

        if dispenseState != ST_DISPENSE:
            break
            
        # proceed to next step...
        
    # all done!
    
    if dispenseState == ST_DISPENSE:
        logger.info('Done dispensing {}'.format(dispenseDrinkOrder.desc()))
        drink.timesDispensed = drink.timesDispensed + 1
        drink.save()
        dispenseDrinkOrder.completedDate = datetime.datetime.now()
        dispenseDrinkOrder.save()
        dispenseState = ST_PICKUP
        # TODO: set lights
        
    dispenseEvent.clear()
    bus.emit('barbot:dispenseState', dispenseState, dispenseDrinkOrder)

    while dispenseState is not None:
        if dispenseEvent.wait(0.5):
            dispenseEvent.clear()
            if dispenseState == ST_CANCEL_CLEAR or dispenseState == ST_PICKUP:
                if not glassReady:
                    dispenseState = None
                    dispenseDrinkOrder = None
            elif dispenseControl == CTL_OK:
                dispenseState = None
                    
    bus.emit('barbot:dispenseState', dispenseState, dispenseDrinkOrder)
         
    _rebuildMenu()
    
    DrinkOrder.deleteOldCompleted()

    
#@bus.on('model:pump:stateChanged')
#def _bus_pumpChanged(pump, previousState):
#    if pump.previousState != Pump.READY and pump.state == Pump.READY:
#    if pump.previousState != Pump.EMPTY and pump.state == Pump.EMPTY:
#        _rebuildMenu()
#    elif pump.previousState == Pump.READY and pump.state != Pump.READY:
#        _rebuildMenu()

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
            