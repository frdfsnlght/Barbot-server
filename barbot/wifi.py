
import sys, os, time, logging, subprocess, re, time
from threading import Thread, Event
from flask_socketio import emit

from .config import config
from .bus import bus
from .socket import socket


wpaSupplicantNetworkBeginPattern    = re.compile(r"\s*network\s*=\s*\{")
wpaSupplicantNetworkEndPattern      = re.compile(r"\s*\}")
wpaSupplicantNetworkSSIDPattern     = re.compile(r"\s*ssid\s*=\s*\"(.+)\"")

wifiStatePattern = re.compile(r"(?i)(?s)SSID:\"([^\"]+)\".*Link Quality=(\d+)/(\d+).*Signal level=(\-?\d+)")
wifiNetworkCellPattern = re.compile(r"(?i)(?s)Quality=(\d+)/(\d+).*Signal level=(\-?\d+).*SSID:\"([^\"]+)\".*Authentication Suites.*?: ([\w ]+)")


logger = logging.getLogger('Wifi')
exitEvent = Event()
thread = None
state = False
wpaSupplicantHeader = []
wpaSupplicantNetworks = []


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
    state = getState()
    if not state:
        logging.info('Wifi not available')
        return
    
    _readWPASupplicant(config.getpath('wifi', 'wpaSupplicantFile'))
    
    thread = Thread(target = _threadLoop, name = 'WifiThread')
    thread.daemon = True
    thread.start()

def _threadLoop():
    global state
    logger.info('Wifi thread started')
    while not exitEvent.is_set():
        state = getState()
        socket.emit('wifiState', state)  # broadcast by default
        exitEvent.wait(config.getint('wifi', 'checkInterval'))
    logger.info('Wifi thread stopped')
    
    
    
def _readWPASupplicant(path):
    global wpaSupplicantHeader, wpaSupplicantNetworks
    wpaSupplicantHeader = []
    wpaSupplicantNetworks = []
    try:
        with open(path) as f:
            content = [line.rstrip() for line in f.readlines()]
        network = False
        for line in content:
            if type(network) is dict:
                m = wpaSupplicantNetworkEndPattern.match(line)
                if m:
                    wpaSupplicantNetworks.append(network)
                    network = False
                    continue
                m = wpaSupplicantNetworkSSIDPattern.match(line)
                if m:
                    network['ssid'] = m.group(1)
                network['content'].append(line)
            elif wpaSupplicantNetworkBeginPattern.match(line):
                network = {
                    'ssid': None,
                    'content': []
                }
            elif line:
                wpaSupplicantHeader.append(line)
    except FileNotFoundError:
        pass
    
def _writeWPASupplicant(path):
    try:
        with open(path, 'w') as f:
            for line in wpaSupplicantHeader:
                f.write(line + '\n')
            for network in wpaSupplicantNetworks:
                f.write('network {\n')
                for line in network['content']:
                    f.write(line + '\n')
                f.write('}\n')
    except IOError as e:
        logger.error(e)
    
def getState():
    return {
        'ssid': 'Bennedum',
        'quality': '40/70',
        'signal': -50,
        'bars': 3,
    }

    try:
        out = subprocess.run(['iwconfig', config.get('wifi', 'interface')],
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True)
    except IOError as e:
        logger.error(e)
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

def getNetworks():
    networks = {}
    
    # add saved networks
    for n in wpaSupplicantNetworks:
        if state and state['ssid'] == n['ssid']:
            network = {**state}
            network['saved'] = True
            network['connected'] = True
        else:
            network = {
                'ssid': n['ssid'],
                'saved': True,
            }
        networks[network['ssid']] = network
    
    #-------------------------------------
    # TODO: remove test code someday
    
    networks['Fake scanned network'] = {
        'ssid': 'Fake scanned network',
        'quality': '40/70',
        'signal': -50,
        'bars': 2,
        'auth': ['WPA2 PSK'],
        'scanned': True,
    }

    # end test code
    #-------------------------------------

    try:
        out = subprocess.run(['sudo', 'iwlist', config.get('wifi', 'interface'), 'scan'], stdout = subprocess.PIPE, stderr = subprocess.STDOUT, universal_newlines = True)
        if out.returncode == 0:
            for cell in re.split(r"Cell ", out.stdout):
                m = wifiNetworkCellPattern.search(cell)
                if m:
                    network = {
                        'ssid': m.group(4).replace('\\x00', ''),
                        'quality': m.group(1) + '/' + m.group(2),
                        'signal': int(m.group(3)),
                        'auth': m.group(5).split(' '),
                        'bars': int(4.9 * float(m.group(1)) / float(m.group(2))),
                        'scanned': True,
                    }
                    network['connected'] = state and state['ssid'] == network['ssid']
                    if network['ssid'] in networks:
                        networks[network['ssid']] = {**network, **networks[network['ssid']]}
                    else:
                        networks[network['ssid']] = network
                
    except IOError as e:
        logger.error(e)
        
    return list(networks.values())

def connectToNetwork(ssid, psk):
    # if it's saved and no psk is provided: move to top, write/reconfigure
    # if it's saved and psk is provided: replace, move to top, write/reconfigure
    # if it's not saved: save, move to top, write/reconfigure
    # TODO: wpa_cli -i <int> reconfigure
    pass
    
def disconnectFromNetwork():
    if state and state['ssid'] == ssid:
        try:
            out = subprocess.run(['wpa_cli', '-i', config.get('wifi', 'interface'), 'disconnect'], stdout = subprocess.PIPE, stderr = subprocess.STDOUT, universal_newlines = True)
            if out.returncode != 0:
                logger.error('Got return status of {} while trying to disconnect from wifi network: {}'.format(out.returncode, out.stdout))
        except IOError as e:
            logger.error(e)

def forgetNetwork(ssid):
    global wpaSupplicantNetworks
    if state and state['ssid'] == ssid:
        disconnectFromNetwork()
    wpaSupplicantNetworks = [n for n in wpaSupplicantNetworks if n['ssid'] != ssid]
    _writeWPASupplicant(config.getpath('wifi', 'wpaSupplicantFile'))

    
# iwconfig
# iwgetid
# iwlist
    
# https://raspberrypi.stackexchange.com/questions/69084/wi-fi-scanning-and-displaying-using-python-run-by-php
    
    