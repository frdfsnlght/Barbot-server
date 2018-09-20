#!/usr/bin/python3

import sys, os, signal, logging
from threading import Thread

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import barbot.paths
import barbot.config

config = barbot.config.load()

import barbot.logging

barbot.logging.configure(config.getboolean('server', 'developmentMode'))
logger = logging.getLogger('Server')

import barbot.events
import barbot.daemon
from barbot.db import db
from barbot.models import DBModels
from barbot.flaskApp import app
from barbot.flaskSocketIO import socket

import barbot.flaskAppHandlers
import barbot.flaskSocketIOHandlers

webThread = None

def catchSIGTERM(signum, stackframe):
    logger.info('caught SIGTERM')
    barbot.events.exitEvent.set()
    
def catchSIGINT(signum, stackframe):
    logger.info('caught SIGINT')
    barbot.events.exitEvent.set()
    
def webThreadLoop():
    host = config.get('server', 'listenAddress')
    port = config.get('server', 'listenPort')
    logger.info('Web thread started on ' + host + ':' + port)
    socket.init_app(app)
    socket.run(
        app,
        host = host,
        port = port,
        debug = False)
    logger.info('Web thread stopped')

def startServer():
    barbot.db.db.connect()
    barbot.db.db.create_tables(barbot.models.DBModels)    
    
    logger.info('Server starting')

    signal.signal(signal.SIGTERM, catchSIGTERM)
    signal.signal(signal.SIGINT, catchSIGINT)
    
    # start threads
    
    webThread = Thread(target = webThreadLoop, name = 'Web')
    webThread.daemon = True
    webThread.start()

    logger.info('Server started')
    
    # wait for the end
    while not barbot.events.exitEvent.is_set():
        barbot.events.exitEvent.wait(1000)
        
    barbot.events.exitEvent.set()
    
    logger.info('Server stopped')

if len(sys.argv) == 2:
    if 'start' == sys.argv[1]:
        if (config.getboolean('server', 'developmentMode')):
            startServer()
        else:
            barbot.daemon.start(startServer)
    elif 'stop' == sys.argv[1]:
        barbot.daemon.stop()
    elif 'restart' == sys.argv[1]:
        barbot.daemon.restart(startServer)
    elif 'status' == sys.argv[1]:
        barbot.daemon.status()
    else:
        print('Unknown command')
        sys.exit(2)
    sys.exit(0)
else:
    print('usage: %s start|stop|restart|status' % sys.argv[0])
    sys.exit(2)

        





