
import os, configparser, logging
from threading import Thread, Event

from . import paths
from .bus import bus


_logger = logging.getLogger('Config')
config = None
_exitEvent = Event()
_thread = None
_lastModifiedTime = None
_defaultConfig = os.path.join(paths.ETC_DIR, 'config-default.ini')
_localConfig = os.path.join(paths.ETC_DIR, 'config.ini')


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
        newTime = max(os.path.getmtime(_defaultConfig), os.path.getmtime(_localConfig))
        if newTime > _lastModifiedTime:
            _lastModifiedTime = newTime
            config.read(_defaultConfig)
            config.read(_localConfig)
            _logger.info('Configuration reloaded')
            bus.emit('config/reloaded')
    
def load():
    global config, _lastModifiedTime
    config = configparser.ConfigParser(
        interpolation = None,
        converters = {
            'path': _resolvePath
        }
    )
    config.optionxform = str    # preserve option case
    config.read(_defaultConfig)
    config.read(_localConfig)
    
    _lastModifiedTime = max(os.stat(_defaultConfig).st_mtime, os.stat(_localConfig).st_mtime)
    
    return config

def _resolvePath(str):
    str = str.replace('!root', paths.ROOT_DIR)
    str = str.replace('!bin', paths.BIN_DIR)
    str = str.replace('!etc', paths.ETC_DIR)
    str = str.replace('!var', paths.VAR_DIR)
    str = str.replace('!content', paths.CONTENT_DIR)
    str = str.replace('!audio', paths.AUDIO_DIR)
    return str
        