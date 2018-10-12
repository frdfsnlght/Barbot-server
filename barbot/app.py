
import os, logging
from flask import Flask, send_from_directory

from . import paths


_logger = logging.getLogger('App')


# create content directory if it doesn't exist
if not (os.path.lexists(paths.CONTENT_DIR) or os.path.exists(paths.CONTENT_DIR)):
    dist = os.path.normpath(os.path.join(paths.ROOT_DIR, '..', 'client', 'dist'))
    _logger.info('Symlinking {} to {}'.format(paths.CONTENT_DIR, dist))
    os.symlink(dist, paths.CONTENT_DIR)

app = Flask(__name__,
    static_url_path = '',
    static_folder = paths.CONTENT_DIR
)



@app.route('/js/<path:path>')
def send_js(path):
    _logger.debug('Request for /js/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/js', path)
    
@app.route('/css/<path:path>')
def send_css(path):
    _logger.debug('Request for /css/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/css', path)
    
@app.route('/fonts/<path:path>')
def send_fonts(path):
    _logger.debug('Request for /fonts/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/fonts', path)
    
@app.route('/img/<path:path>')
def send_img(path):
    _logger.debug('Request for /img/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/img', path)
    
@app.route('/favicon/<path:path>')
def send_favicon(path):
    _logger.debug('Request for /favicon/{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR + '/favicon', path)

@app.route('/audio/<path:path>')
def send_audio(path):
    _logger.debug('Request for /audio/{}'.format(path))
    return send_from_directory(paths.AUDIO_DIR, path)

@app.route('/', defaults = { 'path': ''})
@app.route('/<path:path>')
def index(path):
    _logger.debug('Request for /{}'.format(path))
    return send_from_directory(paths.CONTENT_DIR, 'index.html')


