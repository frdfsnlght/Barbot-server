
import logging, logging.handlers, re

import barbot.config

levelPattern = re.compile(r"^level\.(.*)")

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

    for (k, v) in config.items():
        m = levelPattern.match(k)
        if m:
            logging.getLogger(m.group(1)).setLevel(getattr(logging, v))
