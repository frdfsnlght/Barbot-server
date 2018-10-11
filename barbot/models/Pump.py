
import logging, time, threading, re
from peewee import *
from threading import Lock

from ..db import db, BarbotModel, ModelError, addModel
from ..config import config
from ..bus import bus
from .. import utils
from .. import serial
from .Ingredient import Ingredient


pumpStopEventPattern = re.compile(r"(?i)PS(\d+)")


logger = logging.getLogger('Models.Pump')

pumpExtras = {}

@bus.on('server:start')
def _bus_serverStart():
    pumps = Pump.select()
    if len(pumps) != config.getint('pumps', 'count'):
        logger.warning('Database pump count doesn\'t match configuration count!')
        Pump.delete().execute()
        for i in range(0, config.getint('pumps', 'count')):
            p = Pump()
            p.id = i + 1
            p.save(force_insert = True)
        logger.info('Initialized pumps')

@bus.on('serial:event')
def _bus_serialEvent(e):
    m = pumpStopEventPattern.match(e)
    if m:
        pump = Pump.get_or_none(Pump.id == int(m.group(1)) + 1)
        if pump:
            with pump.lock:
                pump.running = False
                pump.save()
                logger.info('Pump {} stopped'.format(pump.name()))

def anyPumpsRunning():
    for i, p in pumpExtras.items():
        if p.running:
            return True
    return False
    
class PumpExtra(object):
    allAttributes = ['volume', 'running', 'previousState', 'lock']
    dirtyAttributes = ['running']
    
    def __init__(self, pump):
        self.id = pump.id
        
        conf = config.get('pumps', str(self.id))
        if conf:
            conf = conf.split(',')
            self.volume = float(conf[0])
        else:
            self.volume = 0
            
        self.running = False
        self.previousState = pump.state
        self.lock = Lock()
        self.isDirty = False
#        print('PumpExtra created for pump ' + str(id))
        
    def __setattr__(self, attr, value):
        super().__setattr__(attr, value)
#        print('pumpextra.setattr ' + attr + ' = ' + str(value))
        if attr in PumpExtra.dirtyAttributes:
            self.isDirty = True
        

class Pump(BarbotModel):
    ingredient = ForeignKeyField(Ingredient, backref = 'pump', null = True, unique = True)
    containerAmount = FloatField(default = 0)
    amount = FloatField(default = 0)
    units = CharField(default = 'ml')
    state = CharField(null = True)
    
    UNUSED = None
    LOADED = 'loaded'
    READY = 'ready'
    EMPTY = 'empty'
    DIRTY = 'dirty'
    
    @staticmethod
    def getReadyPumps():
        return Pump.select().where(Pump.state == Pump.READY).execute()

    @staticmethod
    def getReadyIngredients():
        return Ingredient.select().join(Pump).where(Pump.state == Pump.READY).execute()
        
    @staticmethod
    def getPumpWithIngredientId(id):
        return Pump.select().where((Pump.state == Pump.READY) & (Pump.ingredient_id == id)).first()
    
    @staticmethod
    def enablePump(id):
        p = Pump.get(Pump.id == id)
        p.enable()
        
    @staticmethod
    def disablePump(id):
        p = Pump.get(Pump.id == id)
        p.disable()
        
    @staticmethod
    def loadPump(params):
        p = Pump.get(Pump.id == int(params['id']))
        p.load(params)

    @staticmethod
    def unloadPump(id):
        p = Pump.get(Pump.id == id)
        p.unload()

    @staticmethod
    def primePump(params, *args, **kwargs):
        p = Pump.get(Pump.id == int(params['id']))
        p.prime(float(params['amount']) if 'amount' in params else p.volume, *args, **kwargs)
        
    @staticmethod
    def drainPump(id, *args, **kwargs):
        p = Pump.get(Pump.id == id)
        p.drain(p.volume * config.getfloat('pumps', 'drainFactor'), *args, **kwargs)
        
    @staticmethod
    def cleanPump(params, *args, **kwargs):
        p = Pump.get(Pump.id == int(params['id']))
        p.clean(float(params['amount']) if 'amount' in params else (p.volume * config.getfloat('pumps', 'cleanFactor')), *args, **kwargs)
        
        
    def save(self, *args, **kwargs):
            
        if self.state == Pump.LOADED or self.state == Pump.READY:
            if not self.containerAmount:
                raise ModelError('container amount is required')
            if not self.amount:
                raise ModelError('amount is required')
            if not self.units:
                raise ModelError('units is required')
            if utils.toML(self.amount, self.units) > utils.toML(self.containerAmount, self.units):
                raise ModelError('amount must be less than container amount')

        emitStateChanged = False
        if 'state' in self.dirty_fields:
            emitStateChanged = True
        if super().save(*args, **kwargs) or self.pumpExtra.isDirty:
            bus.emit('model:pump:saved', self)
            self.pumpExtra.isDirty = False
            if emitStateChanged:
                bus.emit('model:pump:stateChanged', self, self.previousState)
                self.previousState = self.state
        
    def delete_instance(self, *args, **kwargs):
        raise ModelError('pumps cannot be deleted!')
    
    def isReady(self):
        return self.state == Pump.READY
        
    def load(self, params):
        i = Ingredient.get_or_none(Ingredient.id == int(params['ingredientId']))
        if not i:
            raise ModelError('Ingredient not found!')
        params['ingredient'] = i
        if self.state == Pump.UNUSED:
            self.state = Pump.LOADED
            self.set(params)
            self.save()
        elif self.state == Pump.READY or self.state == Pump.EMPTY:
            self.state = Pump.READY
            self.set(params)
            self.save()
            self.ingredient.save(emitEvent = 'force')
        else:
            raise ModelError('Invalid pump state!')
    
    def unload(self):
        if self.state == Pump.LOADED:
            self.state = Pump.UNUSED
            self.ingredient = None
            self.containerAmount = 0
            self.amount = 0
            self.units = 'ml'
            self.save()
        else:
            raise ModelError('Invalid pump state!')
    
    def prime(self, amount, useThread = False):
        if self.state == Pump.LOADED or self.state == Pump.READY:
            if useThread:
                self.forwardAsync(amount)
            else:
                self.forward(amount)
            if self.state != Pump.READY:
                self.state = Pump.READY
                self.save()
        else:
            raise ModelError('Invalid pump state!')

    def drain(self, amount, useThread = False):
        if self.state == Pump.READY or self.state == Pump.EMPTY or self.state == Pump.UNUSED or self.state == Pump.DIRTY:
            if useThread:
                self.reverseAsync(amount)
            else:
                self.reverseAsync(amount)
            if self.state != Pump.UNUSED:
                self.state = Pump.DIRTY
            self.ingredient = None
            self.containerAmount = 0
            self.amount = 0
            self.units = 'ml'
            self.save()
        else:
            raise ModelError('Invalid pump state!')

    def clean(self, amount, useThread = False):
        if self.state == Pump.DIRTY or self.state == Pump.UNUSED:
            if useThread:
                self.forwardAsync(amount)
            else:
                self.forward(amount)
            self.state = Pump.UNUSED
            self.save()
        else:
            raise ModelError('Invalid pump state!')

    def forwardAsync(self, amount):
        threading.Thread(target = self.forward, name = 'PumpThread-{}'.format(self.id), args = [amount], daemon = True).start()
    
    def reverseAsync(self, amount):
        threading.Thread(target = self.reverse, name = 'PumpThread-{}'.format(self.id), args = [amount], daemon = True).start()
    
    # amount is ml!
    def forward(self, amount):
        amount = float(amount)
        logger.info('Pump {} forward {} ml'.format(self.name(), amount))
        
        with self.lock:
            try:
                serial.write('PP{},{},{},{}'.format(
                    self.id - 1,
                    int(amount * config.getfloat('pumps', 'stepsPerML')),
                    config.getint('pumps', 'speed'),
                    config.getint('pumps', 'acceleration')
                ))
                self.running = True
                if self.state == Pump.LOADED or self.state == Pump.READY:
                    self.amount = utils.convertUnits(utils.toML(self.amount, self.units) - amount, 'ml', self.units)
                    if utils.toML(self.amount, self.units) < config.getint('barbot', 'ingredientEmptyAmount'):
                        self.state = Pump.EMPTY
                self.save()
            except serial.SerialError as e:
                logger.error('Pump error: {}'.format(str(e)))
        
        # TODO: remove this
        #time.sleep(amount / 2)
        #self.running = False
        #self.save()
        #logger.info('Pump {} stopped'.format(self.name()))
        
    # amount is ml!
    def reverse(self, amount):
        amount = float(amount)
        logger.info('Pump {} reverse {} ml'.format(self.name(), amount))

        with self.lock:
            try:
                serial.write('PP{},{},{},{}'.format(
                    self.id - 1,
                    -int(amount * config.getfloat('pumps', 'stepsPerML')),
                    config.getint('pumps', 'speed'),
                    config.getint('pumps', 'acceleration')
                ))
                self.running = True
                self.save()
            except serial.SerialError as e:
                logger.error('Pump error: {}'.format(str(e)))
        
        # TODO: remove this
        #time.sleep(amount / 2)
        #self.running = False
        #self.save()
        #logger.info('Pump {} stopped'.format(self.name()))
    
    def stop(self):
        logger.info('Pump {} stop'.format(self.name(), amount))

        with self.lock:
            try:
                serial.write('PH{}'.format(self.id - 1))
                self.running = False
                self.save()
            except serial.SerialError as e:
                logger.error('Pump error: {}'.format(str(e)))
    
    def name(self):
        return '#' + str(self.id)
    
    def set(self, dict):
        if 'ingredient' in dict:
            self.ingredient = dict['ingredient']
        elif 'ingredientId' in dict:
            self.ingredient = int(dict['ingredientId'])
        if 'containerAmount' in dict:
            self.containerAmount = float(dict['containerAmount'])
        if 'units' in dict:
            self.units = str(dict['units'])
        if 'percent' in dict:
            self.amount = (float(dict['percent']) / 100) * self.containerAmount
        elif 'amount' in dict:
            self.amount = float(dict['amount'])
    
    def to_dict(self, ingredient = False):
        out = {
            'id': self.id,
            'name': self.name(),
            'containerAmount': self.containerAmount,
            'amount': self.amount,
            'units': self.units,
            'state': self.state,
            'running': self.running,
        }
        if ingredient:
            if self.ingredient:
                out['ingredientId'] = self.ingredient.id
                out['ingredient'] = self.ingredient.to_dict()
            else:
                out['ingredient'] = None
        return out

    def __getattr__(self, attr):
        if attr == 'pumpExtra':
            if self.id not in pumpExtras:
                pumpExtras[self.id] = PumpExtra(self)
            return pumpExtras[self.id]
        if attr in PumpExtra.allAttributes:
#            print('getattr ' + attr + ' from PumpExtra')
            return getattr(self.pumpExtra, attr)
#        print('getattr ' + attr + ' from myself')
        return super().__getattr__(attr)

    def __setattr__(self, attr, value):
        if attr in PumpExtra.allAttributes:
#            print('setattr ' + attr + ' in PumpExtra')
            setattr(self.pumpExtra, attr, value)
        else:
#            print('pump.setattr ' + attr + ' = ' + str(value))
            super().__setattr__(attr, value)
            
    class Meta:
        database = db
        only_save_dirty = True

addModel(Pump)        
