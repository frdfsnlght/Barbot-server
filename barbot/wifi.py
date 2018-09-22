
import sys, os, time, logging, subprocess, re
from threading import Thread
from flask_socketio import emit

import barbot.config as config
import barbot.events as events
from barbot.socket import socket

logger = logging.getLogger(__name__)
thread = None
state = 'n/a'

wifiStatePattern = re.compile(r"(?i)(?s)SSID:\"([^\"]+)\".*Link Quality=(\d+)/(\d+).*Signal level=(\-?\d+)")


def startThread():
    global thread, state
    if not config.config.getint('wifi', 'checkInterval'):
        logging.info('Wifi checking disabled')
        return
    state = getWifiState()
    if not state:
        logging.info('Wifi not available')
        return
    
    thread = Thread(target = _threadLoop, name = 'WifiThread')
    thread.daemon = True
    thread.start()

def _threadLoop():
    global state
    
    logger.info('Wifi thread started')
    while not events.exitEvent.is_set():
    
        state = getWifiState()
        try:
            socket.emit('wifiState', state)  # broadcast by default
        except:
            # ignore
            pass
            
        events.exitEvent.wait(config.config.getint('wifi', 'checkInterval'))
    logger.info('Wifi thread stopped')
    
def getWifiState():
    try:
        out = subprocess.run(['iwconfig', config.config.get('wifi', 'interface')],
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True)
    except FileNotFoundError:
        # command not found
        return False
    if out.returncode != 0:
        # interface not found 
        return False
    m = wifiStatePattern.search(out.stdout)
    if not m:
        # not connected
        return {
            'ssid': False
        }
    # connected
    state = {
        'ssid': m.group(1),
        'quality': float(m.group(2)) / float(m.group(3)),
        'signal': int(m.group(4))
    }
    state['bars'] = int(state['quality'] * 4.9)
    return state

    
# iwconfig
# iwgetid
# iwlist
# discover networks: sudo iwlist wlan0 scan
    
# https://raspberrypi.stackexchange.com/questions/69084/wi-fi-scanning-and-displaying-using-python-run-by-php
    
# Get connected SSID: iwgetid --raw wlan0

    
def emitState():
    emit('wifiState', state)
    