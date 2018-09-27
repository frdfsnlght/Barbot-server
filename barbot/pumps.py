
import logging

from barbot.models import Pump


DISABLED = None
UNLOADED = 'unloaded'
LOADED = 'loaded'
READY = 'ready'
EMPTY = 'empty'
DIRTY = 'dirty'

logger = logging.getLogger(__name__)

pumps = []

def loadAll():
    global pumps
    pumps = Pump.select()

def getPump(id):
    i = next((index for (index, p) in enumerate(pumps) if p.id == id), None)
    return pumps[i] if i else None

def drain(id):
    logger.info('drain pump ' + str(id))
    
def clean(id):
    logger.info('clean pump ' + str(id))

def prime(id, amount, units):
    logger.info('prime pump ' + str(id) + ' ' + str(amount) + ' ' + units)
    