
import logging, time, threading
from peewee import *

from ..db import db, BarbotModel, ModelError, addModel
from ..config import config
from ..bus import bus
from .. import utils
from .Ingredient import Ingredient


logger = logging.getLogger('Models.Pump')

pumpExtras = {}

class PumpExtra(object):
    attributes = ['volume', 'running']
    
    def __init__(self, id):
        self.id = id
        
        conf = config.get('pumps', str(id))
        if conf:
            conf = conf.split(',')
            self.volume = float(conf[0])
        else:
            self.volume = 0
            
        self.running = False
        self.isDirty = False
#        print('PumpExtra created for pump ' + str(id))
        
    def __setattr__(self, attr, value):
        super().__setattr__(attr, value)
#        print('pumpextra.setattr ' + attr + ' = ' + str(value))
        if attr != 'isDirty':
            self.isDirty = True
        

class Pump(BarbotModel):
    ingredient = ForeignKeyField(Ingredient, backref = 'pump', null = True, unique = True)
    containerAmount = FloatField(default = 0)
    amount = FloatField(default = 0)
    units = CharField(default = 'ml')
    state = CharField(null = True)
    
    DISABLED = None
    UNLOADED = 'unloaded'
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
        p = Pump.get(Pump.id == params['id'])
        p.load(params)

    @staticmethod
    def unloadPump(id):
        p = Pump.get(Pump.id == id)
        p.unload()

    @staticmethod
    def primePump(params, *args, **kwargs):
        p = Pump.get(Pump.id == int(params['id']))
        p.prime(params['amount'] if 'amount' in params else p.volume, *args, **kwargs)
        
#    @staticmethod
#    def reloadPump(params):
#        p = Pump.get(Pump.id == params['id'])
#        p.reload(params)

    @staticmethod
    def drainPump(id, *args, **kwargs):
        p = Pump.get(Pump.id == id)
        p.drain(p.volume * 1.2, *args, **kwargs)
        
    @staticmethod
    def cleanPump(params, *args, **kwargs):
        p = Pump.get(Pump.id == int(params['id']))
        p.clean(params['amount'] if 'amount' in params else (p.volume * 1.5), *args, **kwargs)
        
        
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
                
        if super().save(*args, **kwargs) or self.pumpExtra.isDirty:
            bus.emit('model:pump:saved', self)
            self.pumpExtra.isDirty = False
            
        
    def delete_instance(self, *args, **kwargs):
        raise ModelError('pumps cannot be deleted!')
    
    def enable(self):
        if self.state == Pump.DISABLED:
            self.state = Pump.UNLOADED
            self.save()
        else:
            raise ModelError('Invalid pump state!')
    
    def disable(self):
        if self.state == Pump.UNLOADED:
            self.state = Pump.DISABLED
            self.save()
        else:
            raise ModelError('Invalid pump state!')
    
    def load(self, params):
        i = Ingredient.get_or_none(Ingredient.id == int(params['ingredientId']))
        if not i:
            raise ModelError('Ingredient not found!')
        params['ingredient'] = i
        if self.state == Pump.UNLOADED:
            self.state = Pump.LOADED
            self.set(params)
            self.save()
        elif self.state == Pump.READY or self.state == Pump.EMPTY:
            self.state = Pump.READY
            self.set(params)
            self.save()
        else:
            return error('Invalid pump state!')
    
    def unload(self):
        if self.state == Pump.LOADED:
            self.state = Pump.UNLOADED
            self.ingredient = None
            self.containerAmount = 0
            self.amount = 0
            self.units = 'ml'
            self.save()
        else:
            return error('Invalid pump state!')
    
    def prime(self, amount, useThread = False):
        if self.state == Pump.LOADED or self.state == Pump.READY:
            if useThread:
                threading.Thread(target = self.forward, name = 'PumpThread', args = [amount], daemon = True).start()
            else:
                self.forward(amount)
            if self.state != Pump.READY:
                self.state = Pump.READY
                self.save()
        else:
            return error('Invalid pump state!')

#    def reload(self, params):
#        if self.state == Pump.READY or self.state == Pump.EMPTY:
#            self.state = Pump.READY
#            self.set(params)
#            self.save()
#        else:
#            return error('Invalid pump state!')
    
    def drain(self, amount, useThread = False):
        if self.state == Pump.READY or self.state == Pump.EMPTY:
            if useThread:
                threading.Thread(target = self.reverse, name = 'PumpThread', args = [amount], daemon = True).start()
            else:
                self.reverse(amount)
            self.state = Pump.DIRTY
            self.ingredient = None
            self.containerAmount = 0
            self.amount = 0
            self.units = 'ml'
            self.save()
        else:
            return error('Invalid pump state!')

    def clean(self, amount, useThread = False):
        if self.state == Pump.DIRTY:
            if useThread:
                threading.Thread(target = self.forward, name = 'PumpThread', args = [amount], daemon = True).start()
            else:
                self.forward(amount)
            self.state = Pump.UNLOADED
            self.save()
        else:
            return error('Invalid pump state!')
            
    def forward(self, amount):
        logger.info('pump ' + self.name() + ' forward ' + str(amount) + ' ml')
        
        self.running = True
        self.save()
        
        # TODO: use the serial port
        time.sleep(amount / 2)
    
        self.running = False
        self.save()
        logger.info('pump ' + self.name() + ' stopped')
        
    def reverse(self, amount):
        logger.info('pump ' + self.name() + ' reverse ' + str(amount) + ' ml')
        
        self.running = True
        self.save()
        
        # TODO: use the serial port
        time.sleep(amount / 2)
    
        self.running = False
        self.save()
        logger.info('pump ' + self.name() + ' stopped')
        
    
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
                pumpExtras[self.id] = PumpExtra(self.id)
            return pumpExtras[self.id]
        if attr in PumpExtra.attributes:
#            print('getattr ' + attr + ' from PumpExtra')
            return getattr(self.pumpExtra, attr)
#        print('getattr ' + attr + ' from myself')
        return super().__getattr__(attr)

    def __setattr__(self, attr, value):
        if attr in PumpExtra.attributes:
#            print('setattr ' + attr + ' in PumpExtra')
            setattr(self.pumpExtra, attr, value)
        else:
#            print('pump.setattr ' + attr + ' = ' + str(value))
            super().__setattr__(attr, value)
            
    class Meta:
        database = db
        only_save_dirty = True

addModel(Pump)        
