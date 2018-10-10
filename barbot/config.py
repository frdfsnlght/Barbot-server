
import os, configparser, logging
from threading import Thread, Event

from . import paths
from .bus import bus


logger = logging.getLogger('Config')
config = None
exitEvent = Event()
thread = None
lastModifiedTime = None
defaultConfig = os.path.join(paths.ETC_DIR, 'config-default.ini')
localConfig = os.path.join(paths.ETC_DIR, 'config.ini')


@bus.on('server:start')
def _bus_serverStart():
    global thread
    exitEvent.clear()
    if not config.getint('server', 'configCheckInterval'):
        return
    thread = Thread(target = _threadLoop, name = 'ConfigThread')
    thread.daemon = True
    thread.start()

@bus.on('server:stop')
def _bus_serverStop():
    exitEvent.set()
    
def _threadLoop():
    global lastModifiedTime
    while not exitEvent.is_set():
        exitEvent.wait(config.getfloat('server', 'configCheckInterval'))
        newTime = max(os.stat(defaultConfig).st_mtime, os.stat(localConfig).st_mtime)
        if newTime > lastModifiedTime:
            lastModifiedTime = newTime
            config.read(defaultConfig)
            config.read(localConfig)
            bus.emit('config:reloaded')
            logger.info('Configuration reloaded')
    
def load():
    global config, lastModifiedTime
    config = configparser.ConfigParser(
        interpolation = None,
        converters = {
            'path': resolvePath
        }
    )
    config.optionxform = str    # preserve option case
    config.read(defaultConfig)
    config.read(localConfig)
    
    lastModifiedTime = max(os.stat(defaultConfig).st_mtime, os.stat(localConfig).st_mtime)
    
    return config

def resolvePath(str):
    str = str.replace('!root', paths.ROOT_DIR)
    str = str.replace('!bin', paths.BIN_DIR)
    str = str.replace('!etc', paths.ETC_DIR)
    str = str.replace('!var', paths.VAR_DIR)
    str = str.replace('!content', paths.CONTENT_DIR)
    str = str.replace('!audio', paths.AUDIO_DIR)
    return str
        