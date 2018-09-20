
import os, logging
from flask import Flask

import barbot.paths as paths

logger = logging.getLogger(__name__)

# create content directory if it doesn't exist
if not (os.path.lexists(paths.CONTENT_DIR) or os.path.exists(paths.CONTENT_DIR)):
    logger.info('creating content directory ' + paths.CONTENT_DIR)
    os.makedirs(paths.CONTENT_DIR)
        
app = Flask(__name__,
    static_url_path = '',
    static_folder = paths.CONTENT_DIR
)


#app.config.from_object('config.Configuration')


