
import logging
from peewee import *

from ..db import db, BarbotModel, addModel
from ..bus import bus
from .Drink import Drink
from .Ingredient import Ingredient


logger = logging.getLogger('Models.DrinkIngredient')


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

    def toDict(self, drink = False, ingredient = False):
        out = {
            'id': self.id,
            'drinkId': self.drink.id,
            'ingredientId': self.ingredient.id,
            'amount': self.amount,
            'units': self.units,
            'step': self.step,
        }
        if drink:
            out['drink'] = self.drink.toDict()
        if ingredient:
            out['ingredient'] = self.ingredient.toDict()
        return out
        
    class Meta:
        database = db
        only_save_dirty = True
        indexes = (
            (('drink', 'ingredient'), True),
        )

addModel(DrinkIngredient)
