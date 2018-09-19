
import logging, logging.handlers

import barbot.config

def configure(console = False):
    config = barbot.config.config['logging']
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.get('logLevel')))
    
    handler = logging.handlers.RotatingFileHandler(
        config.getpath('logFile'),
        maxBytes = config.getint('logSize'),
        backupCount = config.getint('logCount'))
        
    handler.setFormatter(logging.Formatter(fmt = config.get('logFormat')))
    root.addHandler(handler)

    if console:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt = config.get('logFormat')))
        root.addHandler(handler)

    # turn down socket IO logging
    logging.getLogger('socketio').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    