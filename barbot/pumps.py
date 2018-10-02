
import logging

from .bus import bus
from .models.Pump import Pump

logger = logging.getLogger(__name__)


def drain(id):
    logger.info('drain pump ' + str(id))
    
def clean(id):
    logger.info('clean pump ' + str(id))

def prime(id, amount, units):
    logger.info('prime pump ' + str(id) + ' ' + str(amount) + ' ' + units)
    