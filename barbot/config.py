
import os, configparser, logging
from threading import Thread, Event

from .bus import bus


_logger = logging.getLogger('Config')
config = None
_exitEvent = Event()
_thread = None
_lastModifiedTime = None
_rootDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_defaultConfig = os.path.join(_rootDir, 'etc', 'config-default.ini')
_localConfig = os.path.join(_rootDir, 'etc', 'config.ini')


@bus.on('server/start')
def _bus_serverStart():
    global _thread
    _exitEvent.clear()
    if not config.getint('server', 'configCheckInterval'):
        return
    _thread = Thread(target = _threadLoop, name = 'ConfigThread')
    _thread.daemon = True
    _thread.start()

@bus.on('server/stop')
def _bus_serverStop():
    _exitEvent.set()
    
def _threadLoop():
    global _lastModifiedTime
    while not _exitEvent.is_set():
        _exitEvent.wait(config.getfloat('server', 'configCheckInterval'))
        if max(os.path.getmtime(_defaultConfig), os.path.getmtime(_localConfig)) > _lastModifiedTime:
            _load()
    
def load():
    global config, _lastModifiedTime
    config = configparser.ConfigParser(
        interpolation = None,
        converters = {
            'path': _resolvePath
        }
    )
    config.optionxform = str    # preserve option case
    _load()
    return config

def _load():
    global _lastModifiedTime
    _lastModifiedTime = max(os.stat(_defaultConfig).st_mtime, os.stat(_localConfig).st_mtime)
    config.clear()
    config.read(_defaultConfig)
    config.read(_localConfig)
    _logger.info('Configuration loaded')
    bus.emit('config/loaded')

def _resolvePath(str):
    if os.path.isabs(str):
        return str
    else:
        return os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), str))
        
#    str = str.replace('!root', paths.ROOT_DIR)
#    str = str.replace('!bin', paths.BIN_DIR)
#    str = str.replace('!etc', paths.ETC_DIR)
#    str = str.replace('!var', paths.VAR_DIR)
#    str = str.replace('!content', paths.CONTENT_DIR)
#    str = str.replace('!audio', paths.AUDIO_DIR)
#    return str
        