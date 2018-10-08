
import functools
from flask import session
from flask_socketio import SocketIO

from .config import config


socket = SocketIO()


def success(d = None, **kwargs):
    out = {'error': False, **kwargs}
    if type(d) is dict:
        out = {**out, **d}
    return out
#    return {'error': False}

def error(msg):
    return {'error': str(msg)}

def userLoggedIn():
    return 'user' in session

def userIsAdmin():
    return 'user' in session and session['user'].isAdmin

def checkAdmin(clientOpt):
    b = config.getboolean('client', clientOpt)
    return userIsAdmin() if b else True
    
def requireUser(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if userLoggedIn():
            return f(*args, **kwargs)
        else:
            return error('Permission denied!')
    return wrapped
    
def requireAdmin(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if userIsAdmin():
            return f(*args, **kwargs)
        else:
            return error('Permission denied!')
    return wrapped
    