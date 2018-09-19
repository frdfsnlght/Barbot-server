#!/usr/bin/python3

import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import barbot.paths
import barbot.config

config = barbot.config.load()

from barbot.db import db
from barbot.models import DBModels, Glass, Ingredient, Drink, DrinkIngredient

db.connect()
db.create_tables(DBModels)

glasses = [
    ('Coffee mug', 16, 'oz', 'Your basic coffee mug.'),
    ('Highball', 16, 'oz', 'Classic highball glass.'),
    ('Highball', 8, 'oz', 'Classic highball glass.'),
    ('Cocktail', 8, 'oz', 'Classic cocktail glass.'),
    ('Shot glass', 1, 'oz', 'Standard shot glass.')
]

Glass.delete().execute()
Glass.insert_many(glasses, fields=[Glass.type, Glass.size, Glass.units, Glass.description]).execute()
for glass in Glass.select():
    print(str(glass.size) + ' ' + glass.units + ' ' + glass.type)
    




