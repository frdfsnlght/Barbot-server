
import functools, logging, re
from flask import request, session
from flask_socketio import SocketIO, emit

from .config import config
from .bus import bus
from . import barbot
from . import wifi


booleanPattern = re.compile(r"(i?)(true|false|yes|no)")
intPattern = re.compile(r"-?\d+$")
floatPattern = re.compile(r"-?\d*\.\d+$")


logger = logging.getLogger('Socket')
socket = SocketIO()
consoleSessionId = None


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
    
@socket.on('connect')
def _socket_connect():
    global consoleSessionId
    logger.info('Connection opened from ' + request.remote_addr)
    emit('clientOptions', _buildClientOptions())
    emit('dispenserHold', barbot.dispenserHold)
    emit('pumpSetup', barbot.pumpSetup)
    emit('glassReady', barbot.glassReady)
    emit('parentalLock', True if barbot.getParentalCode() else False)
    emit('dispenseState', {'state': barbot.dispenseState, 'order': barbot.dispenseDrinkOrder})
    emit('wifiState', wifi.state)
    bus.emit('socket:connect', request)
    if not consoleSessionId and request.remote_addr == '127.0.0.1':
        consoleSessionId = request.sid
        bus.emit('socket:consoleConnect')

@socket.on('disconnect')
def _socket_disconnect():
    global consoleSessionId
    logger.info('Connection closed from ' + request.remote_addr)
    bus.emit('socket:disconnect', request)
    if request.sid == consoleSessionId:
        consoleSessionId = None
        bus.emit('socket:consoleDisconnect')
    
    
    
@bus.on('config:reloaded')
def _but_configReloaded():
    socket.emit('clientOptions', _buildClientOptions())
    
@bus.on('wifi:state')
def _bus_wifiState(state):
    socket.emit('wifiState', state)
    
@bus.on('socket:playAudio')
def _bus_playAudio(file, console, sessionId, broadcast):
    if broadcast:
        logger.debug('Play {} everywhere'.format(file))
        socket.emit('playAudio', file)
    else:
        if sessionId:
            logger.debug('Play {} on client {}'.format(file, sessionId))
            socket.emit('playAudio', file, room = sessionId)
        if console and consoleSessionId:
            logger.debug('Play {} on console'.format(file))
            socket.emit('playAudio', file, room = consoleSessionId)


    
    
def _buildClientOptions():
    opts = dict(config.items('client'))
    for k, v in opts.items():
        if booleanPattern.match(v):
            opts[k] = config.getboolean('client', k)
        elif intPattern.match(v):
            opts[k] = config.getint('client', k)
        elif floatPattern.match(v):
            opts[k] = config.getfloat('client', k)
    return opts
            