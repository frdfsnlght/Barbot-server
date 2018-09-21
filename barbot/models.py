
import datetime
from peewee import *

from barbot.db import db


class Glass(Model):
    type = CharField()
    size = IntegerField()
    units = CharField()
    description = TextField(null = True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'size': self.size,
            'units': self.units,
            'description' : self.description,
        }
        
    class Meta:
        database = db
        indexes = (
            (('type', 'size', 'units'), True),
        )

class Ingredient(Model):
    name = CharField(unique = True)
    isAlcoholic = BooleanField(default = True)
    timesDispensed = IntegerField(default = 0)
    amountDispensed = FloatField(default = 0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'isAlcoholic': self.isAlcoholic,
            'timesDispensed': self.timesDispensed,
            'amountDispensed': self.amountDispensed,
        }
    
    class Meta:
        database = db

class Drink(Model):
    primaryName = CharField()
    secondaryName = CharField()
    instructions = TextField(null = True)
    timesDispensed = IntegerField(default = 0)
    isFavorite = BooleanField(default = False)
    glass = ForeignKeyField(Glass, backref = 'drinks')

    createdDate = DateTimeField(default = datetime.datetime.now)
    updatedDate = DateTimeField(default = datetime.datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'primaryName': self.primaryName,
            'secondaryName': self.secondaryName,
            'instructions': self.instructions,
            'timesDispensed': self.timesDispensed,
            'isFavorite': self.isFavorite,
            'glass': self.glass.to_dict(),
            'createdDate': self.createdDate,
            'updatedDate': self.updatedDate,
        }
    
    class Meta:
        database = db
        indexes = (
            (('primaryName', 'secondaryName'), True),
        )

class DrinkIngredient(Model):
    drink = ForeignKeyField(Drink, backref = 'ingredients')
    ingredient = ForeignKeyField(Ingredient, backref = 'drinks')
    amount = FloatField

    class Meta:
        database = db
        indexes = (
            (('drink', 'ingredient'), True),
        )

class DrinkOrder(Model):
    drink = ForeignKeyField(Drink, backref = 'orders')
    name = CharField(null = True)
    createdDate = DateTimeField(default = datetime.datetime.now)
    onHold = BooleanField(default = False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'drink': self.drink.to_dict(),
            'name': self.name,
            'createdDate': self.createdDate,
            'onHold': self.onHold,
        }
    
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

