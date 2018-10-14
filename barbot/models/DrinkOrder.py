
import logging, datetime, os
from peewee import *

from ..db import db, BarbotModel, addModel
from ..bus import bus
from ..config import config
from .Drink import Drink


_logger = logging.getLogger('Models.DrinkOrder')


@bus.on('server/start')
def _bus_serverStart():
    DrinkOrder.clearSessionIds()
    
class DrinkOrder(BarbotModel):
    drink = ForeignKeyField(Drink, backref = 'orders')
    name = CharField(null = True)
    createdDate = DateTimeField(default = datetime.datetime.now)
    startedDate = DateTimeField(null = True)
    completedDate = DateTimeField(null = True)
    ingredientHold = BooleanField(default = False)
    userHold = BooleanField(default = False)
    sessionId = CharField(null = True)
    
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
    def deleteOldCompleted(secondsOld):
        num = DrinkOrder.delete().where(
                    DrinkOrder.completedDate < (datetime.datetime.now() - datetime.timedelta(seconds = secondsOld))
                ).execute()
        if num:
            _logger.info('Deleted {} old drink orders'.format(num))
        
    @staticmethod
    def clearSessionIds():
        DrinkOrder.update(sessionId = None).execute()
        
    @staticmethod
    def submitFromDict(item):
        o = DrinkOrder()
        o.set(item)
        o.save()
        return o
        
    @staticmethod
    def cancelById(id):
        o = DrinkOrder.get(DrinkOrder.id == id, DrinkOrder.startedDate.is_null())
        o.delete_instance()
        return o
        
    @staticmethod
    def toggleHoldById(id):
        o = DrinkOrder.get(DrinkOrder.id == id, DrinkOrder.startedDate.is_null())
        o.userHold = not o.userHold
        o.save()
        return o

    # override
    def save(self, *args, **kwargs):
        if super().save(*args, **kwargs):
            bus.emit('model/drinkOrder/saved', self)
        
    # override
    def delete_instance(self, *args, **kwargs):
    
        if self.isBeingDispensed():
            raise ModelError('This order is currently being dispensed!')
            
        for o in self.drinkOrders:
            if o.isWaiting():
                raise ModelError('This drink has a pending order!')
    
        super().delete_instance(*args, **kwargs)
        bus.emit('model/drinkOrder/deleted', self)
            
    def isWaiting(self):
        return self.startedDate is None
        
    def isBeingDispensed(self):
        return self.startedDate and self.completedDate is None
        
    def placeOnHold(self):
        self.startedDate = None
        self.userHold = True
        self.save()
        
    def desc(self):
        return '"{}" for {}'.format(self.drink.name(), self.name if self.name else 'unknown')
        
    def set(self, dict):
        if 'drink' in dict:
            self.drink = dict['drink']
        elif 'drinkId' in dict:
            self.drink = int(dict['drinkId'])
        if 'name' in dict:
            self.name = str(dict['name'])
        if 'userHold' in dict:
            self.userHold = bool(dict['userHold'])
        if 'sessionId' in dict:
            self.sessionId = str(dict['sessionId'])
    
    def toDict(self, drink = False, glass = False):
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
            out['drink'] = self.drink.toDict(glass = glass)
        return out
        
    class Meta:
        database = db
        only_save_dirty = True

addModel(DrinkOrder)
