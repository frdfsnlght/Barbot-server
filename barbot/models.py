
import logging, datetime
from peewee import *

from barbot.db import db

logger = logging.getLogger(__name__)


class BarbotModel(Model):
    pass
            
class Glass(BarbotModel):
    type = CharField()
    size = IntegerField()
    units = CharField()
    description = TextField(null = True)
    
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
        indexes = (
            (('type', 'size', 'units'), True),
        )

class Ingredient(BarbotModel):
    name = CharField(unique = True)
    isAlcoholic = BooleanField(default = True)
    timesDispensed = IntegerField(default = 0)
    amountDispensed = FloatField(default = 0)
    
    def set(self, dict):
        if 'name' in dict:
            self.name = str(dict['name'])
        if 'isAlcoholic' in dict:
            self.isAlcoholic = bool(dict['isAlcoholic'])
    
    def to_dict(self, drinks = False):
        out = {
            'id': self.id,
            'name': self.name,
            'isAlcoholic': self.isAlcoholic,
            'timesDispensed': self.timesDispensed,
            'amountDispensed': self.amountDispensed,
        }
        if drinks:
            out['drinks'] = [di.to_dict(drink = True) for di in self.drinks]
        return out
        
    
    class Meta:
        database = db

class Drink(BarbotModel):
    primaryName = CharField()
    secondaryName = CharField(null = True)
    instructions = TextField(null = True)
    timesDispensed = IntegerField(default = 0)
    isFavorite = BooleanField(default = False)
    glass = ForeignKeyField(Glass, backref = 'drinks')
    isAlcoholic = BooleanField(default = True)
    
    createdDate = DateTimeField(default = datetime.datetime.now)
    updatedDate = DateTimeField(default = datetime.datetime.now)

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
        # update/remove ingredients
        for di in self.ingredients:
            i = next((ingredient for ingredient in ingredients if ingredient['ingredientId'] == di.ingredient.id), None)
            if i:
                di.set(i)
                di.save()
                logger.info('updating ' + str(di.id))
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
            logger.info('add ingredient ' + str(ingredient['ingredientId']))
    
    def to_dict(self, glass = False, ingredients = False):
        out = {
            'id': self.id,
            'primaryName': self.primaryName,
            'secondaryName': self.secondaryName,
            'instructions': self.instructions,
            'timesDispensed': self.timesDispensed,
            'isFavorite': self.isFavorite,
            'isAlcoholic': self.isAlcoholic,
            'createdDate': self.createdDate.isoformat(),
            'updatedDate': self.updatedDate.isoformat(),
            'name': self.name(),
            'glassId': self.glass.id,
        }
        if glass:
            out['glass'] = self.glass.to_dict()
        if ingredients:
            out['ingredients'] = [di.to_dict(ingredient = True) for di in self.ingredients]
        return out
    
    class Meta:
        database = db
        indexes = (
            (('primaryName', 'secondaryName'), True),
        )

class DrinkIngredient(BarbotModel):
    drink = ForeignKeyField(Drink, backref = 'ingredients')
    ingredient = ForeignKeyField(Ingredient, backref = 'drinks')
    amount = FloatField()
    units = CharField()
    step = IntegerField(default = 0)

    def set(self, dict):
        if 'drinkId' in dict:
            self.drink = int(dict['drinkId'])
        if 'ingredientId' in dict:
            self.ingredient = int(dict['ingredientId'])
        if 'amount' in dict:
            self.amount = float(dict['amount'])
        if 'units' in dict:
            self.units = str(dict['units'])
        if 'step' in dict:
            self.step = int(dict['step'])
    
    def ingredientName(self):
        return str(self.amount) + ' ' + self.units + ' ' + self.ingredient.name

    def to_dict(self, drink = False, ingredient = False):
        out = {
            'id': self.id,
            'drinkId': self.drink.id,
            'ingredientId': self.ingredient.id,
            'amount': self.amount,
            'units': self.units,
            'step': self.step,
        }
        if drink:
            out['drink'] = self.drink.to_dict()
        if ingredient:
            out['ingredient'] = self.ingredient.to_dict()
        return out
        
    class Meta:
        database = db
        indexes = (
            (('drink', 'ingredient'), True),
        )

class DrinkOrder(BarbotModel):
    drink = ForeignKeyField(Drink, backref = 'orders')
    name = CharField(null = True)
    createdDate = DateTimeField(default = datetime.datetime.now)
    startedDate = DateTimeField(null = True)
    completedDate = DateTimeField(null = True)
    ingredientHold = BooleanField(default = False)
    userHold = BooleanField(default = False)
    
    def set(self, dict):
        if 'drinkId' in dict:
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
            'startedDate': self.startedDate.isoformat(),
            'completedDate': self.completedDate.isoformat(),
            'ingredientHold': self.ingredientHold,
            'userHold': self.userHold,
        }
        if drink:
            out['drink'] = self.drink.to_dict()
        return out
        
    class Meta:
        database = db

        
class MenuDrink():
    drink = None
    
class Pump():
    bank = None
    number = None
    ingredient = None
    amount = None
    
    

DBModels = [
    Glass,
    Ingredient,
    Drink,
    DrinkIngredient,
    DrinkOrder    ,
]

