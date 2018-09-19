
from flask import Flask

import barbot.paths as paths

app = Flask(__name__,
    static_url_path = '',
    static_folder = paths.CONTENT_DIR
)

#app.config.from_object('config.Configuration')


