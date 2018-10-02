
import logging, datetime
from peewee import *

from barbot.db import *
from barbot.bus import bus
from .Glass import Glass


logger = logging.getLogger('Models.Drink')


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
    def save_from_dict(item):
        if 'id' in item.keys() and item['id'] != False:
            d = Drink.get_or_none(Drink.id == item['id'])
            if not d:
                raise ModelError('Drink not found!')
        else:
            d = Drink()
        d.set(item)
        d.save()
        # handle ingredients
        if 'ingredients' in item:
            d.setIngredients(item['ingredients'])
        
    @staticmethod
    def delete_by_id(id):
        d = Drink.get(Drink.id == item['id'])
        d.delete_instance()
    
    def save(self, *args, **kwargs):
        if self.is_dirty():
            self.updatedDate = datetime.datetime.now()
        if super().save(*args, **kwargs):
            bus.emit('model:drink:saved', self)
        
    def delete_instance(self, *args, **kwargs):
        super().delete_instance(*args, **kwargs)
        bus.emit('model:drink:deleted', self)
    
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

        isAlcoholic = False
        
        # update/remove ingredients
        for di in self.ingredients:
            i = next((ingredient for ingredient in ingredients if ingredient['ingredientId'] == di.ingredient.id), None)
            if i:
                di.set(i)
                di.save()
                isAlcoholic = isAlcoholic | di.ingredient.isAlcoholic
                #logger.info('updating ' + str(di.id))
                ingredients.remove(i)
            else:
                di.delete_instance()
                logger.info('deleted ' + str(di.id))
            
        # add new ingredients
        for ingredient in ingredients:
            di = DrinkIngredient()
            di.drink = self.id
            di.set(ingredient)
            di.save()
            isAlcoholic = isAlcoholic | di.ingredient.isAlcoholic
            logger.info('add ingredient ' + str(ingredient['ingredientId']))
    
        if isAlcoholic != self.isAlcoholic:
            self.isAlcoholic = isAlcoholic
            self.save()
    
    def to_dict(self, glass = False, ingredients = False):
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
            out['glass'] = self.glass.to_dict()
        if ingredients:
            out['ingredients'] = [di.to_dict(ingredient = True) for di in self.ingredients]
        return out
    
    class Meta:
        database = db
        only_save_dirty = True
        indexes = (
            (('primaryName', 'secondaryName'), True),
        )

addModel(Drink)