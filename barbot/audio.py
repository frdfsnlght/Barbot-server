
import os, os.path, configparser, logging, random, subprocess, hashlib, re
from threading import Thread, Event
from queue import LifoQueue, Empty

from .bus import bus
from .config import config


_ttsFilePattern = re.compile(r"^tts-[0-9a-f]+\.mp3$")
_ttsFileFormat = 'tts-{}.mp3'
_phrasesFileName = 'phrases.ini'
_clipsFileName = 'clips.ini'

_logger = logging.getLogger('Audio')
_exitEvent = Event()
_thread = None
_phrasesConfig = None
_clipsConfig = None
_phrasesFile = os.path.join(config.getpath('audio', 'audioDir'), _phrasesFileName)
_clipsFile = os.path.join(config.getpath('audio', 'audioDir'), _clipsFileName)

_lastModifiedTime = None
_playQueue = LifoQueue()
_ttsJobs = []
_clips = {}


@bus.on('server/start')
def _bus_serverStart():
    global _thread, _phrasesConfig, _clipsConfig
    _phrasesConfig = configparser.ConfigParser(
        interpolation = None,
        allow_no_value = True,
    )
    _phrasesConfig.optionxform = str    # preserve option case
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

@bus.on('config/loaded')
def _bus_configLoaded():
    global _phrasesFile, _clipsFile
    ad = config.getpath('audio', 'audioDir')
    _phrasesFile = os.path.join(ad, _phrasesFileName)
    _clipsFile = os.path.join(ad, _clipsFileName)
    _load()
        
@bus.on('socket/consoleConnect')
def _bus_consoleConnect():
    bus.emit('audio/play', 'startup')

def _threadLoop():
    _logger.info('Audio thread started')
    while not _exitEvent.is_set():
        timeout = config.getfloat('audio', 'fileCheckInterval')
        if _ttsJobs:
            timeout = 0.1
            _processTTSJob(_ttsJobs.pop(0))
        try:
            item = _playQueue.get(block = True, timeout = timeout)
            _playClip(item)
        except Empty:
            _checkFiles()
    _logger.info('Audio thread stopped')

@bus.on('audio/play')
def _on_audioPlay(clip, console = True, sessionId = False, broadcast = False):
    _playQueue.put_nowait({
        'clip': clip,
        'console': console,
        'sessionId': sessionId,
        'broadcast': broadcast,
    })
    
def setVolume(volume):
    open(config.getpath('audio', 'volumeFile'), 'w').write(str(volume))
    bus.emit('audio/volume', volume)

def getVolume():
    try:
        return float(open(config.getpath('audio', 'volumeFile')).read().rstrip())
    except IOError:
        return 1
    
def _load():
    global _lastModifiedTime, _ttsJobs
    
    _phrasesConfig.clear()
    _clipsConfig.clear()
    _lastModifiedTime = 0
    
    if os.path.isfile(_phrasesFile):
        _phrasesConfig.read(_phrasesFile)
        _lastModifiedTime = os.path.getmtime(_phrasesFile)
    if os.path.isfile(_clipsFile):
        _clipsConfig.read(_clipsFile)
        _lastModifiedTime = max(_lastModifiedTime, os.path.getmtime(_clipsFile))

    phrasesMap = {}
    _ttsJobs = []
    for clipName in _phrasesConfig.keys():
        for (phrase, weight) in _phrasesConfig.items(clipName):
            weight = 1 if weight is None else float(weight)
            fileName = _phraseToFileName(phrase)
            phrasesMap[phrase] = fileName
            
            if _audioFileExists(fileName):
                if not _clipsConfig.has_section(clipName):
                    _clipsConfig.add_section(clipName)
                _clipsConfig.set(clipName, fileName, str(weight))
            else:
                _ttsJobs.append({
                    'clip': clipName,
                    'phrase': phrase,
                    'fileName': fileName,
                    'weight': weight,
                })
    _updateClips()
    
    if config.getboolean('audio', 'phrasesMap'):
        mapFile = os.path.join(config.getpath('audio', 'audioDir'), 'phrases.map')
        if not phrasesMap:
            if os.path.isfile(mapFile):
                os.remove(mapFile)
        else:
            with open(mapFile, 'w') as file:
                for (phrase, fileName) in phrasesMap.items():
                    file.write('{} = {}\n'.format(phrase, fileName))
    
    if config.getboolean('audio', 'purgePhrases'):
        for file in [f for f in os.listdir(config.getpath('audio', 'audioDir')) if os.path.isfile(os.path.join(config.getpath('audio', 'audioDir'), f)) and _ttsFilePattern.match(f)]:
            if file not in phrasesMap.values():
                _logger.info('Purged TTS file {}'.format(file))
                os.remove(os.path.join(config.getpath('audio', 'audioDir'), file))

    bus.emit('audio/clipsLoaded')
    _logger.info('Audio clips loaded')
        
def _phraseToFileName(phrase):
    langCode = config.get('audio', 'googleTTSLanguageCode')
    voiceName = config.get('audio', 'googleTTSVoiceName')
    return _ttsFileFormat.format(hashlib.md5((langCode + voiceName + phrase).encode()).hexdigest())

def _audioFileExists(fileName):
    return os.path.isfile(os.path.join(config.getpath('audio', 'audioDir'), fileName))
    
def _updateClips():
    global _clips
    _clips = {}
    for clipName in _clipsConfig.keys():
        # validate files, read and total file weights
        clipFiles = {}
        total = 0
        for (file, weight) in _clipsConfig.items(clipName):
            if not _audioFileExists(file):
                _logger.warning('Clip file {} not found!'.format(file))
                continue
            
            weight = 1 if weight is None else float(weight)
            total = total + weight
            clipFiles[file] = weight

        # build clip
        clip = []
        runningTotal = 0
        for (file, weight) in clipFiles.items():
            clip.append((file, runningTotal + (weight / total)))
            runningTotal = runningTotal + (weight / total)
        if clip:
            _clips[clipName] = clip
    
def _checkFiles():
    t = 0
    if os.path.isfile(_phrasesFile):
        t = os.path.getmtime(_phrasesFile)
    if os.path.isfile(_clipsFile):
        t = max(t, os.path.getmtime(_clipsFile))
    if t > _lastModifiedTime:
        _load()

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

def _processTTSJob(job):
    _logger.info('Processing TTS job {}'.format(job['fileName']))
    
    bin = os.path.join(config.getpath('server', 'binDir'), 'googleTTS.py')
    file = os.path.join(config.getpath('audio', 'audioDir'), job['fileName'])
    
    if config.getboolean('audio', 'inProcessTTS'):
        if not tts(job['phrase'], file):
            return
    
    else:
        try:
            out = subprocess.run([bin, job['phrase'], file],
                stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT,
                universal_newlines = True)
        except IOError as e:
            _logger.error(e)
            return
            
        if out.returncode != 0:
            _logger.error('TTS job {} failed'.format(job['fileName']))
            _logger.error(out.stdout)
            return
            
    if not _clipsConfig.has_section(job['clip']):
        _clipsConfig.add_section(job['clip'])
    _clipsConfig.set(job['clip'], job['fileName'], str(job['weight']))
    _updateClips()
    
def tts(phrase, fileName):    
    try:
        from google.cloud import texttospeech
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config.getpath('audio', 'googleApplicationCredentials')
        client = texttospeech.TextToSpeechClient()
        input = texttospeech.types.SynthesisInput(text = phrase)
        voice = texttospeech.types.VoiceSelectionParams(
            language_code = config.get('audio', 'googleTTSLanguageCode'),
            name = config.get('audio', 'googleTTSVoiceName'),
        )
        audio_config = texttospeech.types.AudioConfig(
            audio_encoding = texttospeech.enums.AudioEncoding.MP3
        )
        response = client.synthesize_speech(input, voice, audio_config)
        with open(fileName, 'wb') as file:
            file.write(response.audio_content)
        _logger.info('TTS job saved to {}'.format(fileName))
    except Error as e:
        _logger.exception(e)
    