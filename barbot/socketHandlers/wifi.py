
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
def _socket_connectToWifiNetwork(ssid, password):
    logger.info('connectToWifiNetwork {}'.format(ssid))
    try:
        wifi.connectToNetwork(ssid, password)
        return success()
    except Exception as e:
        return error(e)
    
@socket.on('disconnectFromWifiNetwork')
def _socket_disconnectFromWifiNetwork(ssid):
    logger.info('disconnectFromWifiNetwork {}'.format(ssid))
    try:
        wifi.disconnectFromNetwork(ssid)
        return success()
    except Exception as e:
        return error(e)
    


#@bus.on('wifi:pump:saved')
#def _bus_modelPumpSaved(p):
#    socket.emit('pumpSaved', p.to_dict(ingredient = True))
