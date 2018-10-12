
import functools, logging, re
from flask import request, session
from flask_socketio import SocketIO, emit
from peewee import DoesNotExist

from .config import config
from .bus import bus
from .db import ModelError
from . import core
from . import wifi

from .models.Drink import Drink
from .models.DrinkIngredient import DrinkIngredient
from .models.DrinkOrder import DrinkOrder
from .models.Glass import Glass
from .models.Ingredient import Ingredient
from .models.Pump import Pump
from .models.User import User


_booleanPattern = re.compile(r"(i?)(true|false|yes|no)")
_intPattern = re.compile(r"-?\d+$")
_floatPattern = re.compile(r"-?\d*\.\d+$")


socket = SocketIO()
_logger = logging.getLogger('Socket')
_consoleSessionId = None


def success(d = None, **kwargs):
    out = {'error': False, **kwargs}
    if type(d) is dict:
        out = {**out, **d}
    return out
#    return {'error': False}

def error(msg):
    return {'error': str(msg)}

def userLoggedIn():
    return 'user' in session

def userIsAdmin():
    return 'user' in session and session['user'].isAdmin

def checkAdmin(clientOpt):
    b = config.getboolean('client', clientOpt)
    return userIsAdmin() if b else True
    
def requireUser(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if userLoggedIn():
            return f(*args, **kwargs)
        else:
            return error('Permission denied!')
    return wrapped
    
def requireAdmin(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if userIsAdmin():
            return f(*args, **kwargs)
        else:
            return error('Permission denied!')
    return wrapped
    
@socket.on_error_default  # handles all namespaces without an explicit error handler
def _socket_default_error_handler(e):
    _logger.exception(e)
    return error('An internal error has ocurred!')
    
#================================================================
# socket events
# These events represent the client-side API
#

#-------------------------------
# special
#
    
@socket.on('connect')
def _socket_connect():
    global _consoleSessionId
    _logger.info('Connection opened from ' + request.remote_addr)
    emit('clientOptions', _buildClientOptions())
    emit('dispenserHold', core.dispenserHold)
    emit('pumpSetup', core.pumpSetup)
    emit('glassReady', core.glassReady)
    emit('parentalLock', True if core.getParentalCode() else False)
    emit('dispenseState', {'state': core.dispenseState, 'order': core.dispenseDrinkOrder})
    emit('wifiState', wifi.state)
    bus.emit('socket/connect', request)
    if not _consoleSessionId and request.remote_addr == '127.0.0.1':
        _consoleSessionId = request.sid
        bus.emit('socket/consoleConnect')

@socket.on('disconnect')
def _socket_disconnect():
    global _consoleSessionId
    _logger.info('Connection closed from ' + request.remote_addr)
    bus.emit('socket/disconnect', request)
    if request.sid == _consoleSessionId:
        _consoleSessionId = None
        bus.emit('socket/consoleDisconnect')

@socket.on('login')
def _socket_login(params):
    user = User.authenticate(params['name'], params['password'])
    if not user:
        return error('Login failed')
    else:
        session['user'] = user
        bus.emit('socket/userLoggedIn', user)
        return success(user = user.toDict())
        
@socket.on('logout')
def _socket_logout():
    if 'user' in session:
        bus.emit('socket/userLoggedOut', session['user'])
        del session['user']
    return success()

@socket.on('restart')
def _socket_restart():
    if not checkAdmin('restartRequiresAdmin'):
        return error('Permission denied!')
    _logger.info('Client requested restart')
    core.restart()
    return success()

@socket.on('shutdown')
def _socket_shutdown():
    if not checkAdmin('shutdownRequiresAdmin'):
        return error('Permission denied!')
    _logger.info('Client requested shutdown')
    core.shutdown()
    return success()

@socket.on('setParentalLock')
def _socket_setParentalLock(code):
    _logger.info('setParentalLock')
    core.setParentalLock(code)
    return success()
    
@socket.on('toggleDispenserHold')
def _socket_toggleDispenserHold():
    core.toggleDispenserHold()
    return success()

@socket.on('startPumpSetup')
def _socket_startPumpSetup():
    if not checkAdmin('pumpSetupRequiresAdmin'):
        return error('Permission denied!')
    core.startPumpSetup()
    return success()
    
@socket.on('stopPumpSetup')
def _socket_stopPumpSetup():
    core.stopPumpSetup()
    return success()

@socket.on('submitDrinkOrder')
def _socket_submitDrinkOrder(item):
    item['sessionId'] = request.sid
    try:
        core.submitDrinkOrder(item)
        return success()
    except DoesNotExist:
        return error('Drink not found!')
    except core.CoreError as e:
        return error(e)

@socket.on('cancelDrinkOrder')
def _socket_cancelDrinkOrder(id):
    try:
        core.cancelDrinkOrder(id)
        return success()
    except DoesNotExist:
        return error('Drink order not found!')
        
@socket.on('toggleDrinkOrderHold')
def _socket_toggleDrinkOrderHold(id):
    try:
        core.toggleDrinkOrderHold(id)
        return success()
    except DoesNotExist:
        return error('Drink order not found!')

@socket.on('dispenseControl')
def _socket_dispenseControl(ctl):
    core.setDispenseControl(ctl)
    return success()

@socket.on('getWifiNetworks')
def _socket_getWifiNetworks():
    return success(networks = wifi.getNetworks())
    
@socket.on('connectToWifiNetwork')
def _socket_connectToWifiNetwork(params):
    wifi.connectToNetwork(params)
    return success()
    
@socket.on('disconnectFromWifiNetwork')
def _socket_disconnectFromWifiNetwork(ssid):
    wifi.disconnectFromNetwork(ssid)
    return success()
    
@socket.on('forgetWifiNetwork')
def _socket_forgetWifiNetwork(ssid):
    wifi.forgetNetwork(ssid)
    return success()
    
@socket.on('getGlasses')
def _socket_getGlasses():
    return success(items = [g.toDict() for g in Glass.select()])

@socket.on('getGlass')
def _socket_getGlass(id):
    try:
        g = Glass.get(Glass.id == id)
        return success(item = g.toDict(drinks = True))
    except DoesNotExist:
        return error('Glass not found!')
    
@socket.on('saveGlass')
def _socket_saveGlass(item):
    try:
        Glass.saveFromDict(item)
        return success()
    except ModelError as e:
        return error(e)

@socket.on('deleteGlass')
def _socket_deleteGlass(id):
    logger.info('deleteGlass')
    try:
        Glass.deleteById(id)
        return success()
    except DoesNotExist:
        return error('Glass not found!')
         
@socket.on('getIngredients')
def _socket_getIngredients():
    return success(items = [i.toDict() for i in Ingredient.select()])

@socket.on('getIngredient')
def _socket_getIngredient(id):
    try:
        i = Ingredient.get(Ingredient.id == id)
        return success(item = i.toDict(drinks = True))
    except DoesNotExist:
        return error('Ingredient not found!')
    
@socket.on('saveIngredient')
def _socket_saveIngredient(item):
    try:
        Ingredient.saveFromDict(item)
        return success()
    except ModelError as e:
        return error(e)

@socket.on('deleteIngredient')
def _socket_deleteIngredient(id):
    logger.info('deleteIngredient')
    try:
        Ingredient.deleteById(id)
        return success()
    except DoesNotExist:
        return error('Ingredient not found!')

@socket.on('getDrinks')
def _socket_getDrinks():
    return success(items = [d.toDict(ingredients = True) for d in Drink.select()])
    
@socket.on('getDrink')
def _socket_getDrink(id):
    try:
        d = Drink.get(Drink.id == id)
        return success(item = d.toDict(glass = True, ingredients = True))
    except DoesNotExist:
        return error('Drink not found!')
    
@socket.on('saveDrink')
def _socket_saveDrink(item):
    try:
        Drink.saveFromDict(item)
        return success()
    except DoesNotExist:
        return error('Drink not found!')
    except ModelError as e:
        return error(e)

@socket.on('deleteDrink')
def _socket_deleteDrink(id):
    logger.info('deleteDrink')
    try:
        Drink.deleteById(id)
        return success()
    except DoesNotExist:
        return error('Drink not found!')
         
@socket.on('getDrinksMenu')
def _socket_getDrinksMenu():
    return success(items = [d.toDict() for d in Drink.getMenuDrinks()])
    
@socket.on('getWaitingDrinkOrders')
def _socket_getWaitingDrinkOrders():
    return success(items = [do.toDict(drink = True) for do in DrinkOrder.getWaiting()])

@socket.on('getDrinkOrder')
def _socket_getDrinkOrder(id):
    try:
        o = DrinkOrder.get(DrinkOrder.id == id)
        return success(item = o.toDict(drink = True))
    except DoesNotExist:
        return error('Drink order not found!')
    
@socket.on('getPumps')
def _socket_getPumps():
    return success(items = [p.toDict(ingredient = True) for p in Pump.select()])
    
@socket.on('loadPump')
def _socket_loadPump(params):
    try:
        Pump.loadPump(params)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)

@socket.on('unloadPump')
def _socket_unloadPump(id):
    try:
        Pump.unloadPump(id)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)
    
@socket.on('primePump')
def _socket_primePump(params):
    try:
        Pump.primePump(params, useThread = True)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)
    
@socket.on('drainPump')
def _socket_drainPump(id):
    try:
        Pump.drainPump(id, useThread = True)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)

@socket.on('cleanPump')
def socket_cleanPump(params):
    try:
        Pump.cleanPump(params, useThread = True)
        return success()
    except DoesNotExist:
        return error('Pump not found!')
    except ModelError as e:
        return error(e)


    
    
    
    
#================================================================
# bus events
#
    
#-------------------------------
# misc
#
    
@bus.on('config/reloaded')
def _but_configReloaded():
    socket.emit('clientOptions', _buildClientOptions())
    
#-------------------------------
# core
#
    
@bus.on('core/dispenserHold')
def _bus_dispenserHold(dispenserHold):
    socket.emit('dispenserHold', dispenserHold)
    
@bus.on('core/dispenseState')
def _bus_dispenseState(dispenseState, dispenseDrinkOrder):
    if dispenseDrinkOrder:
        dispenseDrinkOrder = dispenseDrinkOrder.toDict(drink = True, glass = True)
    socket.emit('dispenseState', {'state': dispenseState, 'order': dispenseDrinkOrder})
    
@bus.on('core/pumpSetup')
def _bus_pumpSetup(pumpSetup):
    socket.emit('pumpSetup', pumpSetup)

@bus.on('core/glassReady')
def _bus_glassReady(ready):
    socket.emit('glassReady', ready)
    
@bus.on('core/parentalLock')
def _bus_parentalLock(locked):
    socket.emit('parentalLock', locked)

#-------------------------------
# wifi
#

@bus.on('wifi/state')
def _bus_wifiState(state):
    socket.emit('wifiState', state)
    
#-------------------------------
# audio
#
    
@bus.on('audio/playFile')
def _bus_playFile(file, console, sessionId, broadcast):
    if broadcast:
        _logger.debug('Play {} everywhere'.format(file))
        socket.emit('playAudio', file)
    else:
        if sessionId:
            _logger.debug('Play {} on client {}'.format(file, sessionId))
            socket.emit('playAudio', file, room = sessionId)
        if console and _consoleSessionId:
            _logger.debug('Play {} on console'.format(file))
            socket.emit('playAudio', file, room = _consoleSessionId)

#-------------------------------
# glass
#

@bus.on('model/glass/saved')
def _bus_modelGlassSaved(g):
    socket.emit('glassSaved', g.toDict())

@bus.on('model/glass/deleted')
def _bus_modelGlassDeleted(g):
    socket.emit('glassDeleted', g.toDict())

#-------------------------------
# ingredient
#
            
@bus.on('model/ingredient/saved')
def _bus_modelIngredientSaved(i):
    socket.emit('ingredientSaved', i.toDict())

@bus.on('model/ingredient/deleted')
def _bus_modelIngredientDeleted(i):
    socket.emit('ingredientDeleted', i.toDict())
                 
#-------------------------------
# drink
#

@bus.on('model/drink/saved')
def _bus_modelDrinkSaved(d):
    socket.emit('drinkSaved', d.toDict(glass = True, ingredients = True))

@bus.on('model/drink/deleted')
def _bus_modelDrinkDeleted(d):
    socket.emit('drinkDeleted', d.toDict())
    
#-------------------------------
# drink order
#

@bus.on('model/drinkOrder/saved')
def _bus_modelDrinkOrderSaved(o):
    socket.emit('drinkOrderSaved', o.toDict(drink = True))

@bus.on('model/drinkOrder/deleted')
def _bus_modelDrinkOrderDeleted(o):
    socket.emit('drinkOrderDeleted', o.toDict())
         
#-------------------------------
# pump
#
    
@bus.on('model/pump/saved')
def _bus_modelPumpSaved(p):
    socket.emit('pumpSaved', p.toDict(ingredient = True))


    
def _buildClientOptions():
    opts = dict(config.items('client'))
    for k, v in opts.items():
        if _booleanPattern.match(v):
            opts[k] = config.getboolean('client', k)
        elif _intPattern.match(v):
            opts[k] = config.getint('client', k)
        elif _floatPattern.match(v):
            opts[k] = config.getfloat('client', k)
    return opts
            