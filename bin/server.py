#!/usr/bin/python3

import eventlet
eventlet.monkey_patch()

import sys, os, signal, logging, time
from threading import Thread, Event

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import barbot.paths
import barbot.config

config = barbot.config.load()

import barbot.logging

barbot.logging.configure(config.getboolean('server', 'developmentMode'))
logger = logging.getLogger('Server')

from barbot.bus import bus
import barbot.daemon as daemon
from barbot.db import db, models
from barbot.app import app
from barbot.socket import socket

import barbot.barbot
import barbot.models
import barbot.wifi
import barbot.pumps

import barbot.appHandlers
import barbot.socketHandlers


webThread = None
exitEvent = Event()


def catchSIGTERM(signum, stackframe):
    logger.info('caught SIGTERM')
    exitEvent.set()
    
def catchSIGINT(signum, stackframe):
    logger.info('caught SIGINT')
    exitEvent.set()
    
def webThreadLoop():
    host = config.get('server', 'listenAddress')
    port = config.get('server', 'listenPort')
    logger.info('Web thread started on ' + host + ':' + port)
    socket.init_app(app)
    socket.run(
        app,
        host = host,
        port = port,
        debug = config.getboolean('server', 'socketIODebug'),
        use_reloader  = False)
    logger.info('Web thread stopped')

def startServer():
    db.connect()
    db.create_tables(models)    
    
    logger.info('Server starting')

    signal.signal(signal.SIGTERM, catchSIGTERM)
    signal.signal(signal.SIGINT, catchSIGINT)
    
    # start threads
    
    webThread = Thread(target = webThreadLoop, name = 'WebThread')
    webThread.daemon = True
    webThread.start()

    bus.emit('server:start')
    
    logger.info('Server started')
    
    # wait for the end
    while not exitEvent.is_set():
        exitEvent.wait(1)
        
    bus.emit('server:stop')
    time.sleep(3)
    
    logger.info('Server stopped')

if len(sys.argv) == 2:
    if 'start' == sys.argv[1]:
        if (config.getboolean('server', 'developmentMode')):
            startServer()
        else:
            daemon.start(startServer)
    elif 'stop' == sys.argv[1]:
        daemon.stop()
    elif 'restart' == sys.argv[1]:
        daemon.restart(startServer)
    elif 'status' == sys.argv[1]:
        daemon.status()
    else:
        print('Unknown command')
        sys.exit(2)
    sys.exit(0)
else:
    print('usage: %s start|stop|restart|status' % sys.argv[0])
    sys.exit(2)

        





