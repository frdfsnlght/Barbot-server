
import os, os.path, configparser, logging, random, subprocess
from threading import Thread, Event
from queue import LifoQueue, Empty

from . import paths
from .socket import socket
from .bus import bus
from .config import config


logger = logging.getLogger('Audio')
clipsConfig = None
exitEvent = Event()
thread = None
lastModifiedTime = None
playQueue = LifoQueue()
started = False
consoleSessionId = None
clips = {}


@bus.on('server:start')
def _bus_serverStart():
    global thread, clipsConfig
    clipsConfig = configparser.ConfigParser(
        interpolation = None,
        allow_no_value = True,
    )
    clipsConfig.optionxform = str    # preserve option case
    _load()
    exitEvent.clear()
    thread = Thread(target = _threadLoop, name = 'AudioThread')
    thread.daemon = True
    thread.start()

@bus.on('server:stop')
def _bus_serverStop():
    exitEvent.set()

@bus.on('client:connect')
def _bus_clientConnect(request):
    global consoleSessionId
    if not consoleSessionId and request.remote_addr == '127.0.0.1':
        consoleSessionId = request.sid
        bus.emit('audio:play', 'startup', sessionId = consoleSessionId)

@bus.on('client:disconnect')
def _bus_clientDisconnect(request):
    global consoleSessionId
    if consoleSessionId and request.sid == consoleSessionId:
        consoleSessionId = None

@bus.on('barbot:restart')
def _bus_barbotRestart():
    bus.emit('audio:play', 'barbot:restart')
    
@bus.on('barbot:shutdown')
def _bus_barbotShutdown():
    bus.emit('audio:play', 'barbot:shutdown')

@bus.on('barbot:drinkOrderSubmitted')
def _bus_barbotDrinkOrderSubmitted(o):
    bus.emit('audio:play', 'barbot:drinkOrderSubmitted', remote = True)

@bus.on('barbot:drinkOrderCancelled')
def _bus_barbotDrinkOrderCancelled(o):
    bus.emit('audio:play', 'barbot:drinkOrderCancelled', remote = True)
    
@bus.on('barbot:drinkOrderHoldToggled')
def _bus_barbotDrinkOrderHoldToggled(o):
    bus.emit('audio:play', 'barbot:drinkOrderHoldToggled', remote = True)

@bus.on('barbot:dispenseState')
def _bus_dispenseState(dispenseState, dispenseDrinkOrder, singleClient = False):
    if dispenseState is None:
        bus.emit('audio:play', 'barbot:dispenseState:idle')
    else:
        bus.emit('audio:play', 'barbot:dispenseState:' + dispenseState)


    
def _threadLoop():
    while not exitEvent.is_set():
        try:
            item = playQueue.get(block = True, timeout = config.getfloat('audio', 'clipsCheckInterval'))
            _playClip(item)
        except Empty:
            _checkClipsFile()

@bus.on('audio:play')
def _on_audioPlay(clip, sessionId = False):
    playQueue.put_nowait({
        'clip': clip,
        'sessionId': sessionId,
    })
    
def _load():
    global lastModifiedTime, clips
    if not os.path.isfile(config.getpath('audio', 'clipsFile')):
        return
    clipsConfig.read(config.getpath('audio', 'clipsFile'))
    lastModifiedTime = os.stat(config.getpath('audio', 'clipsFile')).st_mtime
    
    clips = {}
    for clipName in clipsConfig.keys():
        clip = []
        total = 0
        for (file, v) in clipsConfig.items(clipName):
            v = 1 if v is None else float(v)
            total = total + v
        runningTotal = 0
        for (file, v) in clipsConfig.items(clipName):
            v = 1 if v is None else float(v)
            clip.append((file, runningTotal + (v / total)))
            runningTotal = runningTotal + (v / total)
        if clip:
            clips[clipName] = clip

def _checkClipsFile():
    if os.path.isfile(config.getpath('audio', 'clipsFile')):
        newTime = os.stat(config.getpath('audio', 'clipsFile')).st_mtime
        if lastModifiedTime is None or newTime > lastModifiedTime:
            _load()
            bus.emit('audio:clipsReloaded')
            logger.info('Audio clips reloaded')

def _playClip(item):
    if not item['clip'] in clips:
        logger.debug('No configured clips for {}'.format(item['clip']))
        return
    clip = clips[item['clip']]
    r = random.random()
    for file in clip:
        if r < file[1]:
            _playFile(file[0], item['sessionId'])
            return
    logger.error('No file found for {}: r={} !'.format(item['clip'], r))
            
def _playFile(file, sessionId = False):
    logger.debug('Play {} {}'.format(file, sessionId if sessionId else 'broadcast'))

    if sessionId:
        socket.emit('playAudio', file, room = sessionId)
    else:
        socket.emit('playAudio', file)
    
#    fullPath = os.path.join(paths.AUDIO_DIR, file)
#    try:
#        out = subprocess.run(['aplay', fullPath],
#            stdout = subprocess.PIPE,
#            stderr = subprocess.STDOUT,
#            universal_newlines = True)
#    except IOError as e:
#        logger.error(e)
#    if out.returncode != 0:
#        logger.error('Got return status of {} while playing file {}: {}'.format(out.returncode, fullPath, out.stdout.strip()))
    