
import logging, serial, re
from threading import Thread, Event, Lock

from .config import config
from .bus import bus


_commentPattern = re.compile(r"#(.*)")
_errorPattern = re.compile(r"!(.*)")
_eventPattern = re.compile(r"\*(.*)")

_logger = logging.getLogger('Serial')
_exitEvent = Event()
_thread = None
_port = None
_writeLock = Lock()
_responseReceived = Event()
_responseError = None
_responseLines = []


class SerialError(Exception):
    pass
    
@bus.on('server/start')
def _bus_serverStart():
    global _thread
    _exitEvent.clear()
    _thread = Thread(target = _threadLoop, name = 'SerialThread')
    _thread.daemon = True
    _thread.start()
    
    # TODO: send commands to indicate I've started
@bus.on('server/stop')
def _bus_serverStop():
    _exitEvent.set()
    
@bus.on('socket/consoleConnect')
def _bus_consoleConnect():
    try:
        write('RO', timeout = 1)  # power on, turn of lights
    except SerialError as e:
        _logger.error(e)

def _threadLoop():
    global _port
    _logger.info('Serial thread started')
    try:
        _port = serial.Serial(config.get('serial', 'port'), config.getint('serial', 'speed'), timeout = None)
        _logger.info('Serial _port {} opened at {}'.format(_port.name, _port.baudrate))
        while not _exitEvent.is_set():
            _readPort()
    except IOError as e:
        _logger.error(str(e))
        if _port:
            _port.close()
            _port = None
    _logger.info('Serial thread stopped')
    
def _readPort():
    line = _port.readline()
    if line:
        _processLine(line.rstrip().decode('ascii'))

def _processLine(line):
    _logger.debug('got: {}'.format(line))
    
    if line.lower() == 'ok':
        _responseError = None
        _responseReceived.set()
        return
        
    m = _errorPattern.match(line)
    if m:
        _responseError = m.group(1)
        _responseReceived.set()
        return
        
    m = _eventPattern.match(line)
    if m:
        bus.emit('serial/event', m.group(1))
        return
        
    m = _commentPattern.match(line)
    if m:
        _logger.debug('Received: {}'.format(m.group(1)))
        return
        
    _responseLines.append(line)
    
def write(line, timeout = 5):
    global _responseLines, _responseError
    with _writeLock:
        _logger.debug('Sending: {}'.format(line))
        if not _port:
            raise SerialError('serial port is not open')
        _responseLines = []
        _responseError = None
        _responseReceived.clear()
        _port.write((line + '\r\n').encode('ascii'))
        if timeout:
            if not _responseReceived.wait(timeout):
                _responseError = 'timeout'
        else:
            _responseReceived.wait()
        if _responseError:
            raise SerialError(_responseError)
        return _responseLines
   