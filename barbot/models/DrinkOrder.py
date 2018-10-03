
import logging, datetime
from peewee import *

from ..db import db, BarbotModel, addModel
from ..bus import bus
from ..config import config
from .Drink import Drink


logger = logging.getLogger('Models.DrinkOrder')


class DrinkOrder(BarbotModel):
    drink = ForeignKeyField(Drink, backref = 'orders')
    name = CharField(null = True)
    createdDate = DateTimeField(default = datetime.datetime.now)
    startedDate = DateTimeField(null = True)
    completedDate = DateTimeField(null = True)
    ingredientHold = BooleanField(default = False)
    userHold = BooleanField(default = False)
    
    @staticmethod
    def getFirstPending():
        try:
            return DrinkOrder.select().where(
                (DrinkOrder.startedDate.is_null()) &
                (DrinkOrder.ingredientHold == False) &
                (DrinkOrder.userHold == False)
            ).order_by(DrinkOrder.createdDate.asc()).first()
        except DoesNotExist:
            return None
    
    @staticmethod
    def getWaiting():
        return DrinkOrder.select().where(
            DrinkOrder.startedDate.is_null()
        )
    
    @staticmethod
    def deleteOldCompleted():
        num = DrinkOrder.delete().where(
                    DrinkOrder.completedDate < (datetime.datetime.now() - datetime.timedelta(seconds = config.getint('barbot', 'maxDrinkOrderAge')))
                ).execute()
        if num:
            logger.info('deleted ' + str(num) + ' old drink orders')
        
    @staticmethod
    def submit_from_dict(item):
        o = DrinkOrder()
        o.set(item)
        o.save()
        
    @staticmethod
    def cancel_by_id(id):
        o = DrinkOrder.get(DrinkOrder.id == id, DrinkOrder.startedDate.is_null())
        o.delete_instance()

    @staticmethod
    def toggle_hold_by_id(id):
        o = DrinkOrder.get(DrinkOrder.id == id, DrinkOrder.startedDate.is_null())
        o.userHold = not o.userHold
        o.save()

    def save(self, *args, **kwargs):
        if super().save(*args, **kwargs):
            bus.emit('model:drinkOrder:saved', self)
        
    def delete_instance(self, *args, **kwargs):
        super().delete_instance(*args, **kwargs)
        bus.emit('model:drinkOrder:deleted', self)
            
    def set(self, dict):
        if 'drink' in dict:
            self.drink = dict['drink']
        elif 'drinkId' in dict:
            self.drink = int(dict['drinkId'])
        if 'name' in dict:
            self.name = str(dict['name'])
        if 'userHold' in dict:
            self.userHold = bool(dict['userHold'])
    
    def to_dict(self, drink = False):
        out = {
            'id': self.id,
            'drinkId': self.drink.id,
            'name': self.name,
            'createdDate': self.createdDate.isoformat(),
            'startedDate': self.startedDate.isoformat() if self.startedDate else None,
            'completedDate': self.completedDate.isoformat() if self.completedDate else None,
            'ingredientHold': self.ingredientHold,
            'userHold': self.userHold,
        }
        if drink:
            out['drink'] = self.drink.to_dict()
        return out
        
    class Meta:
        database = db
        only_save_dirty = True

addModel(DrinkOrder)
