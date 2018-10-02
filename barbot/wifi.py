
import sys, os, time, logging, subprocess, re
from threading import Thread, Event
from flask_socketio import emit

from .config import config
from .bus import bus
from .socket import socket

logger = logging.getLogger('Wifi')
exitEvent = Event()
thread = None
state = False

wifiStatePattern = re.compile(r"(?i)(?s)SSID:\"([^\"]+)\".*Link Quality=(\d+)/(\d+).*Signal level=(\-?\d+)")
wifiNetworkCellPattern = re.compile(r"(?i)(?s)Quality=(\d+)/(\d+).*Signal level=(\-?\d+).*SSID:\"([^\"]+)\".*Authentication Suites.*?: ([\w ]+)")


@bus.on('server:stop')
def _bus_serverStop():
    exitEvent.set()
    
@bus.on('client:connect')
def _bus_clientConnect():
    emit('wifiState', state)
    
@bus.on('server:start')
def _startThread():
    global thread, state
    exitEvent.clear()
    if not config.getint('wifi', 'checkInterval'):
        logging.info('Wifi checking disabled')
        return
    state = _getWifiState()
    if not state:
        logging.info('Wifi not available')
        return
    
    thread = Thread(target = _threadLoop, name = 'WifiThread')
    thread.daemon = True
    thread.start()

def _threadLoop():
    global state
    
    logger.info('Wifi thread started')
    while not exitEvent.is_set():
    
        state = _getWifiState()
        try:
            socket.emit('wifiState', state)  # broadcast by default
        except:
            # ignore
            pass
            
        exitEvent.wait(config.getint('wifi', 'checkInterval'))
    logger.info('Wifi thread stopped')
    
def _getWifiState():
    try:
        out = subprocess.run(['iwconfig', config.get('wifi', 'interface')],
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

def _getWifiNetworks():
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
    
    