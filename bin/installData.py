#!/usr/bin/python3

import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import barbot.paths
import barbot.config

config = barbot.config.load()

from barbot.db import db
from barbot.models import *

db.connect()
db.create_tables(DBModels)

DrinkOrder.delete().execute()
DrinkIngredient.delete().execute()
Drink.delete().execute()
Ingredient.delete().execute()
Glass.delete().execute()

glasses = [
    ('Coffee mug', 16, 'oz', 'Your basic coffee mug.'),
    ('Highball', 16, 'oz', 'Classic highball glass.'),
    ('Highball', 8, 'oz', 'Classic highball glass.'),
    ('Cocktail', 8, 'oz', 'Classic cocktail glass.'),
    ('Shot glass', 1, 'oz', 'Standard shot glass.')
]

Glass.insert_many(glasses, fields=[Glass.type, Glass.size, Glass.units, Glass.description]).execute()
g1 = Glass.get(Glass.type == 'Highball', Glass.size == 8)
g2 = Glass.get(Glass.type == 'Highball', Glass.size == 16)

ingredients = [
    ('Spiced Rum', True),
    ('White Rum', True),
    ('Coca Cola', False),
]

Ingredient.insert_many(ingredients, fields=[Ingredient.name, Ingredient.isAlcoholic]).execute()
i1 = Ingredient.get(Ingredient.name == 'Spiced Rum')
i2 = Ingredient.get(Ingredient.name == 'White Rum')
i3 = Ingredient.get(Ingredient.name == 'Coca Cola')

drinks = [
    ('Rum and Coke', 'Traditional', '', g1),
    ('Rum and Coke', 'Tab\'s Standard', '', g2),
]

Drink.insert_many(drinks, fields=[Drink.primaryName, Drink.secondaryName, Drink.instructions, Drink.glass]).execute()
d1 = Drink.get(Drink.primaryName == 'Rum and Coke' and Drink.secondaryName == 'Traditional')
d2 = Drink.get(Drink.primaryName == 'Rum and Coke' and Drink.secondaryName == 'Tab\'s Standard')

drinkIngredients = [
    (d1, i2, 1, 'oz'),
    (d1, i3, 4, 'oz'),
    (d2, i1, 2, 'oz'),
    (d2, i3, 6, 'oz'),
]

DrinkIngredient.insert_many(drinkIngredients, fields=[DrinkIngredient.drink, DrinkIngredient.ingredient, DrinkIngredient.amount, DrinkIngredient.units]).execute()

drinkOrders = [
    (d2, 'Tab'),
    (d2, 'Aaron'),
    (d1, 'Kate'),
]

DrinkOrder.insert_many(drinkOrders, fields=[DrinkOrder.drink, DrinkOrder.name]).execute()



print('\nGlasses:')
for glass in Glass.select():
    print(glass.name())
    
print('\nIngredients:')
for ingredient in Ingredient.select():
    print(ingredient.name)
    
print('\nDrinks:')
for drink in Drink.select():
    print(drink.name())
    print('  ' + drink.glass.name())
    for di in drink.ingredients:
        print('  ' + di.ingredientName())
    
print('\nDrink Orders:')
for order in DrinkOrder.select():
    print(order.drink.name())
    




