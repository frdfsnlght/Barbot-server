
import logging
from peewee import *

from ..db import db, BarbotModel, addModel
from ..bus import bus


logger = logging.getLogger('Models.Ingredient')


class Ingredient(BarbotModel):
    name = CharField(unique = True)
    isAlcoholic = BooleanField(default = True)
    timesDispensed = IntegerField(default = 0)
    amountDispensed = FloatField(default = 0)
    
    @staticmethod
    def save_from_dict(item):
        if 'id' in item.keys() and item['id'] != False:
            i = Ingredient.get(Ingredient.id == item['id'])
        else:
            i = Ingredient()
        i.set(item)
        i.save()
        
    @staticmethod
    def delete_by_id(id):
        i = Ingredient.get(Ingredient.id == id)
        i.delete_instance()
        
    def save(self, emitEvent = False, *args, **kwargs):
        if super().save(*args, **kwargs) or emitEvent == 'force':
            bus.emit('model:ingredient:saved', self)
    
    def delete_instance(self, *args, **kwargs):
        super().delete_instance(*args, **kwargs)
        bus.emit('model:ingredient:deleted', self)
    
    def set(self, dict):
        if 'name' in dict:
            self.name = str(dict['name'])
        if 'isAlcoholic' in dict:
            self.isAlcoholic = bool(dict['isAlcoholic'])
    
    def to_dict(self, drinks = False):
        pump = self.pump.first()
        out = {
            'id': self.id,
            'name': self.name,
            'isAlcoholic': self.isAlcoholic,
            'timesDispensed': self.timesDispensed,
            'amountDispensed': self.amountDispensed,
            'isAvailable': pump and pump.isReady(),
        }
        if drinks:
            out['drinks'] = [di.to_dict(drink = True) for di in self.drinks]
        return out
        
    
    class Meta:
        database = db
        only_save_dirty = True

addModel(Ingredient)
