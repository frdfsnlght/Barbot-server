
from flask import request, send_from_directory
import logging

from barbot.flaskApp import app
from barbot.models import *
import barbot.paths as paths

logger = logging.getLogger(__name__)

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory(paths.CONTENT_DIR + '/js', path)
    
@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory(paths.CONTENT_DIR + '/css', path)
    
@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory(paths.CONTENT_DIR + '/img', path)
    
@app.route('/favicon.ico')
def send_favicon():
    return send_from_directory(paths.CONTENT_DIR, '/favicon.ico')

@app.route('/', defaults = { 'path': ''})
@app.route('/<path:path>')
def index(path):
    logger.info('request for ' + path)
    return send_from_directory(paths.CONTENT_DIR, 'index.html')
        
    