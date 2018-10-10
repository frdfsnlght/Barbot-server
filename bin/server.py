#!/usr/bin/python3

import eventlet
eventlet.monkey_patch()

import sys, os, signal, logging, time
from threading import Thread, Event
from peewee import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import barbot.paths
import barbot.config

config = barbot.config.load()

import barbot.logging

barbot.logging.configure(config.getboolean('server', 'developmentMode'))
logger = logging.getLogger('Server')

from barbot.bus import bus
import barbot.daemon as daemon
from barbot.db import db, models, ModelError
from barbot.app import app
from barbot.socket import socket

import barbot.serial
import barbot.barbot
import barbot.models
from barbot.models.User import User
import barbot.wifi
import barbot.lights
import barbot.audio

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
    #time.sleep(3)
    
    logger.info('Server stopped')

def addUser(name = None, fullName = None, password = None, isAdmin = False):
    isAdmin = type(isAdmin) is str and isAdmin.lower() == 'yes'
    try:
        user = User.addUser(name, fullName, password, isAdmin)
        print('User {} added.'.format(user.name))
    except IntegrityError:
        print('User already exists.')
        sys.exit(1)
    except ModelError as e:
        print(str(e))
        sys.exit(1)

def deleteUser(name = None):
    try:
        User.deleteUser(name)
        print('User deleted.')
    except ModelError as e:
        print(str(e))
        sys.exit(1)
        
def userPassword(name = None, password = None):
    try:
        User.setUserPassword(name, password)
        print('Password set.')
    except ModelError as e:
        print(str(e))
        sys.exit(1)
        
if len(sys.argv) >= 2:
    cmd = sys.argv[1].lower()
    
    if cmd == 'start':
        if (config.getboolean('server', 'developmentMode')):
            startServer()
        else:
            daemon.start(startServer)
    elif cmd == 'stop':
        daemon.stop()
    elif cmd == 'restart':
        daemon.restart(startServer)
    elif cmd == 'status':
        daemon.status()
    elif cmd == 'adduser':
        addUser(*sys.argv[2:])
    elif cmd == 'deluser':
        deleteUser(*sys.argv[2:])
    elif cmd == 'userpw':
        userPassword(*sys.argv[2:])
    else:
        print('Unknown command')
        sys.exit(2)
    sys.exit(0)
else:
    print('usage: %s start|stop|restart|status|adduser|deluser|userpw' % sys.argv[0])
    sys.exit(2)

        





