
from flask import Flask

import barbot.paths as paths

app = Flask(__name__,
    static_folder = paths.STATIC_DIR,
    template_folder = paths.TEMPLATE_DIR
)

#app.config.from_object('config.Configuration')


