
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


_sensorEventPattern = re.compile(r"(?i)S(\d)")

_logger = logging.getLogger('Barbot')
_exitEvent = Event()
_thread = None
_requestPumpSetup = False
_suppressMenuRebuild = False
_dispenseEvent = Event()
_lastDrinkOrderCheckTime = time.time()

dispenserHold = False
pumpSetup = False
glassReady = False
dispenseState = None
dispenseControl = None
dispenseDrinkOrder = None


@bus.on('server/start')
def _bus_serverStart():
    global _thread
    _rebuildMenu()
    _exitEvent.clear()
    _thread = Thread(target = _threadLoop, name = 'CoreThread', daemon = True)
    _thread.start()

@bus.on('server/stop')
def _bus_serverStop():
    _exitEvent.set()
    
@bus.on('serial/event')
def _bus_serialEvent(e):
    global glassReady
    m = _sensorEventPattern.match(e)
    if m:
        newGlassReady = m.group(1) == '1'
        if newGlassReady != glassReady:
            glassReady = newGlassReady
            bus.emit('core/glassReady', glassReady)
            _dispenseEvent.set()
            
#-----------------
# TODO: remove this temp code someday
glassThread = None
import os.path
from . import paths
@bus.on('server/start')
def _bus_startGlassThread():
    global glassThread
    glassThread = Thread(target = _glassThreadLoop, name = 'BarbotGlassThread', daemon = True)
    glassThread.start()
def _glassThreadLoop():
    global glassReady
    while not _exitEvent.is_set():
        newGlassReady = os.path.isfile(os.path.join(paths.VAR_DIR, 'glass'))
        if newGlassReady != glassReady:
            glassReady = newGlassReady
            bus.emit('core/glassReady', glassReady)
            _dispenseEvent.set()
        time.sleep(1)
# end of temp code
#---------------------

def restart():
    cmd = config.get('server', 'restartCommand').split(' ')
    out = subprocess.run(cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True)
    if out.returncode != 0:
        _logger.error('Error trying to restart: {}'.format(out.stdout))
        return
    bus.emit('lights/play', 'restart')
    bus.emit('audio/play', 'restart')
    
    
def shutdown():
    cmd = config.get('server', 'shutdownCommand').split(' ')
    out = subprocess.run(cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True)
    if out.returncode != 0:
        _logger.error('Error trying to shutdown: {}'.format(out.stdout))
    return
    bus.emit('lights/play', 'shutdown')
    bus.emit('audio/play', 'shutdown')
    
def toggleDispenserHold():
    global dispenserHold
    dispenserHold = not dispenserHold
    bus.emit('core/dispenserHold', dispenserHold)
    
def startPumpSetup():
    global _requestPumpSetup
    _requestPumpSetup = True
    
def stopPumpSetup():
    global _requestPumpSetup, pumpSetup
    _requestPumpSetup = False
    pumpSetup = False
    _rebuildMenu()
    bus.emit('core/pumpSetup', pumpSetup)

def setParentalLock(code):
    if not code:
        try:
            os.remove(config.getpath('barbot', 'parentalCodeFile'))
        except IOError:
            pass
    else:
        open(config.getpath('barbot', 'parentalCodeFile'), 'w').write(code)
    bus.emit('core/parentalLock', True if code else False)

def getParentalCode():
    try:
        return open(config.getpath('barbot', 'parentalCodeFile')).read().rstrip()
    except IOError:
        return False

def submitDrinkOrder(item):
    d = Drink.get(Drink.id == item['drinkId'])
    if d.isAlcoholic:
        code = getParentalCode()
        if code:
            if not 'parentalCode' in item:
                raise CoreError('Parental code required!')
            if item['parentalCode'] != code:
                raise CoreError('Invalid parental code!')
    o = DrinkOrder.submitFromDict(item)
    bus.emit('core/drinkOrderSubmitted', o)
    bus.emit('audio/play', 'drinkOrderSubmitted', sessionId = o.sessionId)

def cancelDrinkOrder(id):
    o = DrinkOrder.cancelById(id)
    bus.emit('core/drinkOrderCancelled', o)
    bus.emit('audio/play', 'drinkOrderCancelled', sessionId = o.sessionId)
        
def toggleDrinkOrderHold(id):
    o = DrinkOrder.toggleHoldById(id)
    bus.emit('core/drinkOrderHoldToggled', o)
    bus.emit('audio/play', 'drinkOrderOnHold' if o.userHold else 'drinkOrderOffHold', sessionId = o.sessionId)
    
def setDispenseControl(ctl):
    global dispenseControl
    dispenseControl = ctl
    _dispenseEvent.set()
        
def _threadLoop():
    global _lastDrinkOrderCheckTime, _requestPumpSetup, pumpSetup
    _logger.info('Core thread started')
    while not _exitEvent.is_set():
        if _requestPumpSetup:
            _requestPumpSetup = False
            pumpSetup = True
            bus.emit('core/pumpSetup', pumpSetup)
            
        while pumpSetup or dispenserHold or anyPumpsRunning():
            time.sleep(1)
        
        
        if (time.time() - _lastDrinkOrderCheckTime) > 5:
            _lastDrinkOrderCheckTime = time.time()
            o = DrinkOrder.getFirstPending()
            if o:
                _dispenseDrinkOrder(o)
                time.sleep(1)
        else:
            time.sleep(1)
            
    _logger.info('Core thread stopped')
    
def _dispenseDrinkOrder(o):
    global dispenseState, dispenseDrinkOrder, dispenseControl
    # this gets the drink out of the queue
    o.startedDate = datetime.datetime.now()
    o.save()
    
    dispenseDrinkOrder = o
    _logger.info('Preparing to dispense {}'.format(dispenseDrinkOrder.desc()))
    
    # wait for user to start or cancel the order
    
    dispenseState = ST_START
    _dispenseEvent.clear()
    dispenseControl = None
    bus.emit('core/dispenseState', dispenseState, dispenseDrinkOrder)
    bus.emit('lights/play', 'waitForDispense')
    bus.emit('audio/play', 'waitForDispense')
    
    while True:
        _dispenseEvent.wait()
        _dispenseEvent.clear()
        # glassReady or dispenseControl changed
        
        if dispenseControl == CTL_CANCEL:
            _logger.info('Cancelled dispensing {}'.format(dispenseDrinkOrder.desc()))
            dispenseDrinkOrder.placeOnHold()
            bus.emit('lights/play', None)
            bus.emit('audio/play', 'cancelledDispense')
            bus.emit('audio/play', 'drinkOrderOnHold', sessionId = dispenseDrinkOrder.sessionId)
            dispenseDrinkOrder = None
            dispenseState = None
            bus.emit('core/dispenseState', dispenseState, dispenseDrinkOrder)

            return
        
        if dispenseControl == CTL_START and glassReady:
            dispenseState = ST_DISPENSE
            bus.emit('core/dispenseState', dispenseState, dispenseDrinkOrder)
            bus.emit('lights/play', 'startDispense')
            bus.emit('audio/play', 'startDispense')
            _logger.info('Starting to dispense {}'.format(dispenseDrinkOrder.desc()))
            break
    
    drink = dispenseDrinkOrder.drink
    dispenseControl = None
    
    for step in sorted({i.step for i in drink.ingredients}):
    
        ingredients = [di for di in drink.ingredients if di.step == step]
        _logger.info('Executing step {}, {} ingredients'.format(step, len(ingredients)))
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

            if _dispenseEvent.wait(0.1):
                _dispenseEvent.clear()
                
                if not glassReady:
                    _logger.warning('Glass removed while dispensing {}'.format(dispenseDrinkOrder.desc()))
                    for pump in pumps:
                        pump.stop()
                    bus.emit('lights/play', 'glassRemovedDispense')
                    bus.emit('audio/play', 'glassRemovedDispense')
                    bus.emit('audio/play', 'drinkOrderOnHold', sessionId = dispenseDrinkOrder.sessionId)
                    dispenseDrinkOrder.placeOnHold()
                    dispenseDrinkOrder = None
                    dispenseState = ST_GLASS_CLEAR

                if dispenseControl == CTL_CANCEL:
                    _logger.info('Cancelled dispensing {}'.format(dispenseDrinkOrder.desc()))
                    for pump in pumps:
                        pump.stop()
                    bus.emit('lights/play', None)
                    bus.emit('audio/play', 'cancelledDispense')
                    bus.emit('audio/play', 'drinkOrderOnHold', sessionId = dispenseDrinkOrder.sessionId)
                    dispenseDrinkOrder.placeOnHold()
                    dispenseDrinkOrder = None
                    dispenseState = ST_CANCEL_CLEAR

        if dispenseState != ST_DISPENSE:
            break
            
        # proceed to next step...
        
    # all done!
    
    if dispenseState == ST_DISPENSE:
        _logger.info('Done dispensing {}'.format(dispenseDrinkOrder.desc()))
        drink.timesDispensed = drink.timesDispensed + 1
        drink.save()
        dispenseDrinkOrder.completedDate = datetime.datetime.now()
        dispenseDrinkOrder.save()
        dispenseState = ST_PICKUP
        bus.emit('lights/play', 'endDispense')
        bus.emit('audio/play', 'endDispense')
        bus.emit('audio/play', 'endDispense', sessionId = dispenseDrinkOrder.sessionId)
        
    _dispenseEvent.clear()
    bus.emit('core/dispenseState', dispenseState, dispenseDrinkOrder)

    while dispenseState is not None:
        if _dispenseEvent.wait(0.5):
            _dispenseEvent.clear()
            if dispenseState == ST_CANCEL_CLEAR or dispenseState == ST_PICKUP:
                if not glassReady:
                    dispenseState = None
                    dispenseDrinkOrder = None
            elif dispenseControl == CTL_OK:
                dispenseState = None
                    
    bus.emit('core/dispenseState', dispenseState, dispenseDrinkOrder)
    bus.emit('lights/play', None)
         
    _rebuildMenu()
    
    DrinkOrder.deleteOldCompleted()

    
@bus.on('model/drink/saved')
def _bus_drinkSaved(drink):
    if not _suppressMenuRebuild:
        _rebuildMenu()

@bus.on('model/drink/deleted')
def _bus_drinkDeleted(drink):
    _rebuildMenu()
    
@db.atomic()
def _rebuildMenu():
    global _suppressMenuRebuild
    _logger.info('Rebuilding drinks menu')
    _suppressMenuRebuild = True
    menuUpdated = False
    ingredients = Pump.getReadyIngredients()
    menuDrinks = Drink.getMenuDrinks()

    # trivial case
    if not ingredients:
        for drink in menuDrinks:
            drink.isOnMenu = False
            drink.save()
            menuUpdated = True
        
    else:
        for drink in Drink.getDrinksWithIngredients(ingredients):
            # remove this drink from the existing menu drinks
            menuDrinks = [d for d in menuDrinks if d.id != drink.id]
            
            onMenu = True
            # check for all the drink's ingredients
            for di in drink.ingredients:
                pump = Pump.getPumpWithIngredientId(di.ingredient_id)
                if not pump or pump.state == Pump.EMPTY or utils.toML(pump.amount, pump.units) < utils.toML(di.amount, di.units):
                    onMenu = False
                    break
            if onMenu != drink.isOnMenu:
                drink.isOnMenu = onMenu
                drink.save()
                menuUpdated = True
    
        # any drinks in the original list are no longer on the menu
        for drink in menuDrinks:
            drink.isOnMenu = False
            drink.save()
            menuUpdated = True
            
    bus.emit('barbot/drinksMenuUpdated')
        
    _updateDrinkOrders()
    _suppressMenuRebuild = False

@db.atomic()
def _updateDrinkOrders():
    _logger.info('Updating drink orders')
    readyPumps = Pump.getReadyPumps()
    for o in DrinkOrder.getWaiting():
        if o.drink.isOnMenu == o.ingredientHold:
            o.ingredientHold = not o.drink.isOnMenu
            o.save()
            