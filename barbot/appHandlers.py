
from flask import send_from_directory
import logging

from .app import app
from . import paths


logger = logging.getLogger('AppHandlers')


@app.route('/js/<path:path>')
def send_js(path):
    logger.debug('Request for /js/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/js', path)
    
@app.route('/css/<path:path>')
def send_css(path):
    logger.debug('Request for /css/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/css', path)
    
@app.route('/fonts/<path:path>')
def send_fonts(path):
    logger.debug('Request for /fonts/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/fonts', path)
    
@app.route('/img/<path:path>')
def send_img(path):
    logger.debug('Request for /img/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/img', path)
    
@app.route('/favicon/<path:path>')
def send_favicon(path):
    logger.debug('Request for /favicon/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/favicon', path)

@app.route('/audio/<path:path>')
def send_audio(path):
    logger.debug('Request for /audio/{}'.format(path))
    return send_from_directory(paths.AUDIO_DIR, path)

@app.route('/', defaults = { 'path': ''})
@app.route('/<path:path>')
def index(path):
    logger.debug('Request for /{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR, 'index.html')
        
    