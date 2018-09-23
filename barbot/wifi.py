
import sys, os, time, logging, subprocess, re
from threading import Thread
from flask_socketio import emit

import barbot.config as config
import barbot.events as events
from barbot.socket import socket

logger = logging.getLogger(__name__)
thread = None
state = False

wifiStatePattern = re.compile(r"(?i)(?s)SSID:\"([^\"]+)\".*Link Quality=(\d+)/(\d+).*Signal level=(\-?\d+)")
wifiNetworkCellPattern = re.compile(r"(?i)(?s)Quality=(\d+)/(\d+).*Signal level=(\-?\d+).*SSID:\"([^\"]+)\".*Authentication Suites.*?: ([\w ]+)")


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
        'quality': m.group(2) + '/' + m.group(3),
        'signal': int(m.group(4)),
        'bars': int(4.9 * float(m.group(2)) / float(m.group(3)))
    }
    return state

def getWifiNetworks():
    try:
        out = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], stdout = subprocess.PIPE, stderr = subprocess.STDOUT, universal_newlines = True)
    except FileNotFoundError:
        # command not found
        return False
    if out.returncode != 0:
        # interface not found 
        return False
    networks = []
    for cell in re.split(r"Cell ", out.stdout):
        m = wifiNetworkCellPattern.search(cell)
        if m:
            network = {
                'quality': m.group(1) + '/' + m.group(2),
                'signal': int(m.group(3)),
                'ssid': m.group(4).replace('\\x00', ''),
                'auth': m.group(5).split(' '),
                'bars': int(4.9 * float(m.group(1)) / float(m.group(2)))
            }
            networks.append(network)
    return networks

    
# iwconfig
# iwgetid
# iwlist
    
# https://raspberrypi.stackexchange.com/questions/69084/wi-fi-scanning-and-displaying-using-python-run-by-php
    
def emitState():
    emit('wifiState', state)
    