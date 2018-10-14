
import logging

from .bus import bus
from .config import config
from . import serial


def colorPercent(r, g, b):
    return '{}:{}:{}'.format(int(r * 255), int(g * 255), int(b * 255))
    
def colorByte(r, g, b):
    return '{}:{}:{}'.format(r, g, b)
    

COLOR_OFF = colorByte(0,0,0)
COLOR_WHITE_100 = colorPercent(1, 1, 1)
COLOR_WHITE_50 = colorPercent(0.5, 0.5, 0.5)

SEGMENTS_MAIN = '0'
SEGMENTS_ALL = '1:2:3:4'


_logger = logging.getLogger('Lights')


@bus.on('server/start')
def _bus_serverStart():
    savePattern(0, config.get('lights', 'startupPattern'))
    #savePattern(1, config.get('lights', 'shutdownPattern'))

@bus.on('lights/play')
def _bus_play(patternName):
    if patternName is None:
        setColor(SEGMENTS_MAIN, COLOR_OFF)
    else:
        pattern = config.get('lights', patternName + 'Pattern')
        if pattern:
            playPattern(pattern)
        
def setColor(segments, color):
    if config.getboolean('lights', 'enabled'):
        _sendCommand('LC{},{}'.format(segments, color))
    
def playPattern(pattern):
    if config.getboolean('lights', 'enabled'):
        _sendCommand('LP{}'.format(pattern))
    
def savePattern(slot, pattern):
    if config.getboolean('lights', 'enabled'):
        _sendCommand('LS{},{}'.format(int(slot), pattern))
    
def loadPattern(slot):
    if config.getboolean('lights', 'enabled'):
        _sendCommand('LL{}'.format(int(slot)))
    
def _sendCommand(cmd):
    try:
        serial.write(cmd)
    except serial.SerialError as e:
        _logger.error('Lights error: {}'.format(str(e)))
