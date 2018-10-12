
import logging
from peewee import *

from ..db import db, BarbotModel, ModelError, addModel
from ..bus import bus


_logger = logging.getLogger('Models.Glass')


class Glass(BarbotModel):
    type = CharField()
    size = IntegerField()
    units = CharField()
    description = TextField(null = True)
    
    @staticmethod
    def saveFromDict(item):
        if 'id' in item.keys() and item['id'] != False:
            g = Glass.get(Glass.id == item['id'])
        else:
            g = Glass()
        g.set(item)
        g.save()
        
    @staticmethod
    def deleteById(id):
        g = Glass.get(Glass.id == item['id'])
        g.delete_instance()
        
    # override
    def save(self, *args, **kwargs):
    
        g = Glass.select().where(Glass.type == self.type, Glass.size == self.size, Glass.units == self.units).first()
        if g and self.id != g.id:
            raise ModelError('The same glass already exists!')
    
        if super().save(*args, **kwargs):
            bus.emit('model/glass/saved', self)

    # override
    def delete_instance(self, *args, **kwargs):
        super().delete_instance(*args, **kwargs)
        bus.emit('model/glass/deleted', self)
            
    def set(self, dict):
        if 'type' in dict:
            self.type = str(dict['type'])
        if 'size' in dict:
            self.size = int(dict['size'])
        if 'units' in dict:
            self.units = str(dict['units'])
        if 'description' in dict:
            self.description = str(dict['description'])
    
    def name(self):
        return str(self.size) + ' ' + self.units + ' ' + self.type
        
    def toDict(self, drinks = False):
        out = {
            'id': self.id,
            'type': self.type,
            'size': self.size,
            'units': self.units,
            'description' : self.description,
            'name': self.name()
        }
        if drinks:
            out['drinks'] = [d.toDict() for d in self.drinks]
        return out
        
    class Meta:
        database = db
        only_save_dirty = True
        indexes = (
            (('type', 'size', 'units'), True),
        )

addModel(Glass)
