
import logging

from barbot.events import bus
from barbot.models import Pump

logger = logging.getLogger(__name__)


def drain(id):
    logger.info('drain pump ' + str(id))
    
def clean(id):
    logger.info('clean pump ' + str(id))

def prime(id, amount, units):
    logger.info('prime pump ' + str(id) + ' ' + str(amount) + ' ' + units)
    