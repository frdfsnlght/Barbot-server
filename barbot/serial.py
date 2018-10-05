
import logging, serial, re
from threading import Thread, Event, Lock

from .config import config
from .bus import bus


commentPattern = re.compile(r"#(.*)")
errorPattern = re.compile(r"!(.*)")
eventPattern = re.compile(r"~(.*)")

logger = logging.getLogger('Serial')
exitEvent = Event()
thread = None
port = None
writeLock = Lock()
responseReceived = Event()
responseError = None
responseLines = []


@bus.on('server:stop')
def _bus_serverStop():
    exitEvent.set()
    
@bus.on('server:start')
def _startThread():
    global thread
    exitEvent.clear()
    thread = Thread(target = _threadLoop, name = 'SerialThread')
    thread.daemon = True
    thread.start()

def _threadLoop():
    global port
    logger.info('Serial thread started')
    port = serial.Serial(config.get('serial', 'port'), config.getint('serial', 'speed'), timeout = None)
    logger.info('Serial port {} opened at {}'.format(port.name, port.baudrate))
    
    while not exitEvent.is_set():
        _readPort()

    port.close()
    logger.info('Serial thread stopped')
    
def _readPort():
    line = port.readline()
    if line:
        _processLine(line.rstrip().decode('ascii'))

def _processLine(line):
    logger.debug('got: {}'.format(line))
    
    if line == 'OK':
        responseError = None
        responseReceived.set()
        return
        
    m = errorPattern.match(line)
    if m:
        responseError = m.group(1)
        responseReceived.set()
        return
        
    m = eventPattern.match(line)
    if m:
        bus.emit('serial:event', m.group(1))
        return
        
    m = commentPattern.match(line)
    if m:
        logger.debug('Received: {}'.format(m.group(1)))
        return
        
    responseLines.append(line)
    
def write(line):
    with writeLock:
        responseLines = []
        responseError = None
        responseReceived.clear()
        port.write((line + '\n').encode('ascii'))
        responseReceived.wait()
        return {
            'lines': responseLines,
            'error': responseError
        }
   