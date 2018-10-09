
import logging
from flask_socketio import emit

from ..bus import bus
from ..socket import socket, success, error
from .. import wifi


logger = logging.getLogger('Socket.Wifi')


@socket.on('getWifiNetworks')
def _socket_getWifiNetworks():
    logger.info('getWifiNetworks')
    return success(networks = wifi.getNetworks())
    
@socket.on('connectToWifiNetwork')
def _socket_connectToWifiNetwork(params):
    logger.info('connectToWifiNetwork {}'.format(params))
    bus.emit('wifi:connectToNetwork', params)
    return success()
    
@socket.on('disconnectFromWifiNetwork')
def _socket_disconnectFromWifiNetwork(ssid):
    logger.info('disconnectFromWifiNetwork {}'.format(ssid))
    bus.emit('wifi:disconnectFromNetwork', ssid)
    return success()
    
@socket.on('forgetWifiNetwork')
def _socket_forgetWifiNetwork(ssid):
    logger.info('forgetWifiNetwork {}'.format(ssid))
    bus.emit('wifi:forgetNetwork', ssid)
    return success()
