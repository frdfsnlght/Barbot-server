
import os, os.path, configparser, logging, random, subprocess
from threading import Thread, Event
from queue import LifoQueue, Empty

from .socket import socket
from .bus import bus
from .config import config


_logger = logging.getLogger('Audio')
_clipsConfig = None
_exitEvent = Event()
_thread = None
_lastModifiedTime = None
_playQueue = LifoQueue()
_clips = {}


@bus.on('server/start')
def _bus_serverStart():
    global _thread, _clipsConfig
    _clipsConfig = configparser.ConfigParser(
        interpolation = None,
        allow_no_value = True,
    )
    _clipsConfig.optionxform = str    # preserve option case
    _load()
    _exitEvent.clear()
    _thread = Thread(target = _threadLoop, name = 'AudioThread')
    _thread.daemon = True
    _thread.start()

@bus.on('server/stop')
def _bus_serverStop():
    _exitEvent.set()

@bus.on('socket/consoleConnect')
def _bus_consoleConnect():
    bus.emit('audio/play', 'startup')


def _threadLoop():
    _logger.info('Audio thread started')
    while not _exitEvent.is_set():
        try:
            item = _playQueue.get(block = True, timeout = config.getfloat('audio', 'clipsCheckInterval'))
            _playClip(item)
        except Empty:
            _checkClipsFile()
    _logger.info('Audio thread stopped')

@bus.on('audio/play')
def _on_audioPlay(clip, console = True, sessionId = False, broadcast = False):
    _playQueue.put_nowait({
        'clip': clip,
        'console': console,
        'sessionId': sessionId,
        'broadcast': broadcast,
    })
    
def _load():
    global _lastModifiedTime, _clips
    if not os.path.isfile(config.getpath('audio', 'clipsFile')):
        return
    _clipsConfig.clear()
    _clipsConfig.read(config.getpath('audio', 'clipsFile'))
    _lastModifiedTime = os.path.getmtime(config.getpath('audio', 'clipsFile'))
    
    _clips = {}
    for clipName in _clipsConfig.keys():
        # validate files, read and total file weights
        clipFiles = {}
        total = 0
        for (file, v) in _clipsConfig.items(clipName):
            if not os.path.isfile(os.path.join(config.getpath('audio', 'audioDir'), file)):
                _logger.warning('Clip file {} not found!'.format(file))
                continue
            
            v = 1 if v is None else float(v)
            total = total + v
            clipFiles[file] = v

        # build clip
        clip = []
        runningTotal = 0
        for (file, v) in clipFiles.items():
            clip.append((file, runningTotal + (v / total)))
            runningTotal = runningTotal + (v / total)
        if clip:
            _clips[clipName] = clip
            
def _checkClipsFile():
    if os.path.isfile(config.getpath('audio', 'clipsFile')):
        newTime = os.path.getmtime(config.getpath('audio', 'clipsFile'))
        if _lastModifiedTime is None or newTime > _lastModifiedTime:
            _load()
            bus.emit('audio/clipsReloaded')
            _logger.info('Audio clips reloaded')

def _playClip(item):
    if not item['clip'] in _clips:
        _logger.debug('No configured clips for {}'.format(item['clip']))
        return
    clipName = item['clip']
    del(item['clip'])
    clip = _clips[clipName]
    r = random.random()
    for file in clip:
        if r < file[1]:
            bus.emit('audio/playFile', **{'file': file[0], **item})
            return
    _logger.warning('No file found for {}!'.format(clipName))

