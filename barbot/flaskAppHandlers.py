
from flask import request
import logging

from barbot.flaskApp import app
from barbot.models import *

logger = logging.getLogger(__name__)


@app.route('/')
def homepage():
    return 'Hello'


