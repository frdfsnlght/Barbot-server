
import logging
from peewee import *

from ..db import db, BarbotModel, addModel
from ..bus import bus


logger = logging.getLogger('Models.Glass')


class Glass(BarbotModel):
    type = CharField()
    size = IntegerField()
    units = CharField()
    description = TextField(null = True)
    
    @staticmethod
    def save_from_dict(item):
        if 'id' in item.keys() and item['id'] != False:
            g = Glass.get(Glass.id == item['id'])
        else:
            g = Glass()
        g.set(item)
        g.save()
        
    @staticmethod
    def delete_by_id(id):
        g = Glass.get(Glass.id == item['id'])
        g.delete_instance()
        
    def save(self, *args, **kwargs):
        if super().save(*args, **kwargs):
            bus.emit('model:glass:saved', self)

    def delete_instance(self, *args, **kwargs):
        super().delete_instance(*args, **kwargs)
        bus.emit('model:glass:deleted', self)
            
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
        
    def to_dict(self, drinks = False):
        out = {
            'id': self.id,
            'type': self.type,
            'size': self.size,
            'units': self.units,
            'description' : self.description,
            'name': self.name()
        }
        if drinks:
            out['drinks'] = [d.to_dict() for d in self.drinks]
        return out
        
    class Meta:
        database = db
        only_save_dirty = True
        indexes = (
            (('type', 'size', 'units'), True),
        )

addModel(Glass)
