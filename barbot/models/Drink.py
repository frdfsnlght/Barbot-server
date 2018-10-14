
import logging, datetime
from peewee import *

from ..db import db, BarbotModel, ModelError, addModel
from ..bus import bus
from ..config import config
from .. import utils

from .Glass import Glass


_logger = logging.getLogger('Models.Drink')


class Drink(BarbotModel):
    primaryName = CharField()
    secondaryName = CharField(null = True)
    glass = ForeignKeyField(Glass, backref = 'drinks')
    instructions = TextField(null = True)
    isFavorite = BooleanField(default = False)
    isAlcoholic = BooleanField(default = True)
    isOnMenu = BooleanField(default = False)
    timesDispensed = IntegerField(default = 0)
    createdDate = DateTimeField(default = datetime.datetime.now)
    updatedDate = DateTimeField(default = datetime.datetime.now)

    @staticmethod
    def getMenuDrinks():
        return Drink.select().where(Drink.isOnMenu == True).execute()

    @staticmethod
    def getDrinksWithIngredients(ingredients):
        from .DrinkIngredient import DrinkIngredient
        return Drink.select(Drink).distinct().join(DrinkIngredient).where(DrinkIngredient.ingredient.in_(list(ingredients))).execute()

    @staticmethod
    @db.atomic()
    def saveFromDict(item):
        if 'id' in item.keys() and item['id'] != False:
            d = Drink.get(Drink.id == item['id'])
        else:
            d = Drink()
        d.set(item)
        if 'ingredients' in item:
            if d.get_id() is None:
                d.save(emitEvent = False)
            d.setIngredients(item['ingredients'])
        d.save()
        
    @staticmethod
    def deleteById(id):
        d = Drink.get(Drink.id == id)
        d.delete_instance()
    
    # override
    def save(self, emitEvent = True, *args, **kwargs):
    
        d = Drink.select().where(Drink.primaryName == self.primaryName, Drink.secondaryName == self.secondaryName).first()
        if d and self.id != d.id:
            raise ModelError('A drink with the same name already exists!')
    
        if self.is_dirty():
            self.updatedDate = datetime.datetime.now()
        if super().save(*args, **kwargs):
            if emitEvent:
                bus.emit('model/drink/saved', self)
        
    # override
    def delete_instance(self, *args, **kwargs):
    
        for o in self.orders:
            if o.isWaiting():
                raise ModelError('This drink has a pending order!')
    
        super().delete_instance(*args, **kwargs)
        bus.emit('model/drink/deleted', self)
    
    def set(self, dict):
        if 'primaryName' in dict:
            self.primaryName = str(dict['primaryName'])
        if 'secondaryName' in dict:
            self.secondaryName = str(dict['secondaryName'])
        if 'instructions' in dict:
            self.instructions = str(dict['instructions'])
        if 'isAlcoholic' in dict:
            self.isAlcoholic = bool(dict['isAlcoholic'])
        if 'glassId' in dict:
            self.glass = int(dict['glassId'])
    
    def name(self):
        return self.primaryName + (('/' + self.secondaryName) if self.secondaryName else '')
        
    def setIngredients(self, ingredients):
        from .DrinkIngredient import DrinkIngredient

        # don't allow more than 4 ingredients in the same step
        if len(ingredients) >= 4:
            for step in {i['step'] for i in ingredients}:
                stepIngs = [i for i in ingredients if i['step'] == step]
                if len(stepIngs) >= 4:
                    raise ModelError('There are already 4 ingredients in the same step!')

        # don't allow more ingredients than configured
        totalMLs = 0
        for i in ingredients:
            totalMLs = totalMLs + utils.toML(float(i['amount']), i['units'])
        if totalMLs > config.getint('client', 'drinkSizeLimit'):
            raise ModelError('Drink ingredients exceed configured limit!')
            
        isAlcoholic = False
        
        # update/remove ingredients
        for di in self.ingredients:
            i = next((ingredient for ingredient in ingredients if ingredient['ingredientId'] == di.ingredient.id), None)
            if i:
                di.set(i)
                di.save()
                isAlcoholic = isAlcoholic | di.ingredient.isAlcoholic
                #_logger.info('updating ' + str(di.id))
                ingredients.remove(i)
            else:
                di.delete_instance()
                _logger.info('deleted ' + str(di.id))
            
        # add new ingredients
        for ingredient in ingredients:
            di = DrinkIngredient()
            di.drink = self.id
            di.set(ingredient)
            di.save()
            isAlcoholic = isAlcoholic | di.ingredient.isAlcoholic
            _logger.info('add ingredient ' + str(ingredient['ingredientId']))
    
        self.isAlcoholic = isAlcoholic
    
    def toDict(self, glass = False, ingredients = False):
        out = {
            'id': self.id,
            'primaryName': self.primaryName,
            'secondaryName': self.secondaryName,
            'glassId': self.glass.id,
            'instructions': self.instructions,
            'isFavorite': self.isFavorite,
            'isAlcoholic': self.isAlcoholic,
            'isOnMenu': self.isOnMenu,
            'timesDispensed': self.timesDispensed,
            'createdDate': self.createdDate.isoformat(),
            'updatedDate': self.updatedDate.isoformat(),
            'name': self.name(),
        }
        if glass:
            out['glass'] = self.glass.toDict()
        if ingredients:
            out['ingredients'] = [di.toDict(ingredient = True) for di in self.ingredients]
        return out
    
    class Meta:
        database = db
        only_save_dirty = True
        indexes = (
            (('primaryName', 'secondaryName'), True),
        )

addModel(Drink)
