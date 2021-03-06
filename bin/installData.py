#!/usr/bin/python3

import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import barbot.paths
import barbot.config

config = barbot.config.load()

from barbot.db import db, models
from barbot.models.Pump import Pump
from barbot.models.DrinkOrder import DrinkOrder
from barbot.models.DrinkIngredient import DrinkIngredient
from barbot.models.Drink import Drink
from barbot.models.Ingredient import Ingredient
from barbot.models.Glass import Glass

db.connect()
db.create_tables(models)

Pump.delete().execute()
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
    ('Light Rum', True),
    ('Dark Rum', True),
    ('Gin', True),
    ('Vodka', True),
    ('Scotch', True),
    ('Bourbon', True),
    ('Tequila', True),
    ('Grenadine', True),
    ('Cachaca', True),
    ('Coca Cola', False),
    ('Sprite', False),
    ('Lime Juice', False),
    ('Lemon Juice', False),
    ('Cranberry Juice', False),
    ('Sugar Syrup', False),
    ('Water', False),
]

Ingredient.insert_many(ingredients, fields=[Ingredient.name, Ingredient.isAlcoholic]).execute()
i1 = Ingredient.get(Ingredient.name == 'Spiced Rum')
i2 = Ingredient.get(Ingredient.name == 'Light Rum')
i3 = Ingredient.get(Ingredient.name == 'Coca Cola')
i4 = Ingredient.get(Ingredient.name == 'Water')

drinks = [
    ('Rum and Coke', 'Traditional', '', True, g1),
    ('Rum and Coke', 'Tab\'s Standard', '', True, g2),
    ('Water', None, '', False, g1),
]

Drink.insert_many(drinks, fields=[Drink.primaryName, Drink.secondaryName, Drink.instructions, Drink.isAlcoholic, Drink.glass]).execute()
d1 = Drink.get(Drink.primaryName == 'Rum and Coke' and Drink.secondaryName == 'Traditional')
d2 = Drink.get(Drink.primaryName == 'Rum and Coke' and Drink.secondaryName == 'Tab\'s Standard')
d3 = Drink.get(Drink.primaryName == 'Water' and Drink.secondaryName.is_null())
d2.isFavorite = True
d2.save()

drinkIngredients = [
    (d1, i2, 1, 'oz', 1),
    (d1, i3, 4, 'oz', 2),
    (d2, i1, 2, 'oz', 1),
    (d2, i3, 6, 'oz', 2),
    (d3, i4, 8, 'oz', 1),
]

DrinkIngredient.insert_many(drinkIngredients, fields=[DrinkIngredient.drink, DrinkIngredient.ingredient, DrinkIngredient.amount, DrinkIngredient.units, DrinkIngredient.step]).execute()

drinkOrders = [
    (d2, 'Tab'),
    (d2, 'Aaron'),
    (d1, 'Kate'),
]

DrinkOrder.insert_many(drinkOrders, fields=[DrinkOrder.drink, DrinkOrder.name]).execute()

for i in range(0, 16):
    p = Pump()
    
    if i == 0:
        p.ingredient = i1
        p.amount = 750
        p.units = 'ml'
        p.containerAmount = 750
        p.state = 'ready'
    elif i == 1:
        p.ingredient = i3
        p.amount = 2000
        p.units = 'ml'
        p.containerAmount = 2000
        p.state = 'ready'
        
    p.save()
    

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
    
print('\nPumps:')
for pump in Pump.select():
    print(pump.name() + ': ' + str(pump.state) + ' ' + str(pump.ingredient))
    
   
#o = DrinkOrder.getFirstPending()
#print(o.to_dict())




