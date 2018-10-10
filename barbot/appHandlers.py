
from flask import request, send_from_directory
import logging

from .app import app
from . import paths


logger = logging.getLogger(__name__)


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory(paths.CONTENT_DIR + '/js', path)
    
@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory(paths.CONTENT_DIR + '/css', path)
    
@app.route('/fonts/<path:path>')
def send_fonts(path):
    return send_from_directory(paths.CONTENT_DIR + '/fonts', path)
    
@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory(paths.CONTENT_DIR + '/img', path)
    
@app.route('/favicon/<path:path>')
def send_favicon(path):
    return send_from_directory(paths.CONTENT_DIR + '/favicon', path)

@app.route('/audio/<path:path>')
def send_audio(path):
    return send_from_directory(paths.AUDIO_DIR, path)

@app.route('/', defaults = { 'path': '/'})
@app.route('/<path:path>')
def index(path):
    logger.info('request for ' + path)
    return send_from_directory(paths.CONTENT_DIR, 'index.html')
        
    