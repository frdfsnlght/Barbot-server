
import logging
from peewee import *

from barbot.db import db, BarbotModel, ModelError, addModel
from .Ingredient import Ingredient


logger = logging.getLogger('Models.Pump')


class Pump(BarbotModel):
    number = IntegerField()
    name = CharField()
    ingredient = ForeignKeyField(Ingredient, backref = 'pump', null = True, unique = True)
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
    
    def save(*args, **kwargs):
        if super().save(*args, **kwargs):
            bus.emit('model:pump:saved', self)
        
    def delete_instance(*args, **kwargs):
        raise ModelError('pumps cannot be deleted!')
            
    def set(self, dict):
        if 'ingredient' in dict:
            self.ingredient = dict['ingredient']
        elif 'ingredientId' in dict:
            self.ingredient = int(dict['ingredientId'])
        if 'amount' in dict:
            self.amount = float(dict['amount'])
        if 'units' in dict:
            self.units = str(dict['units'])
    
    def to_dict(self, ingredient = False):
        out = {
            'id': self.id,
            'number': self.number,
            'name': self.name,
            'amount': self.amount,
            'units': self.units,
            'state': self.state,
        }
        if ingredient and self.ingredient:
            out['ingredientId'] = self.ingredient.id
            out['ingredient'] = self.ingredient.to_dict()
        return out
        
    class Meta:
        database = db
        only_save_dirty = True

addModel(Pump)        
