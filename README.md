# Barbot-server
Barbot's server.

## Prerequisites
* python3
* flask
* flask-socketio
* eventlet
* peewee
* event-bus
* pyserial
* passlib
* bcrypt

## TODO
* use lights
* sound
* limit drink size to configurable amount
* validate foreign key on_delete/on_update settings
* rename server.py to barbot.py
* figure out db export/import
* merge repos into one
* refactor code
* make all model method names camelCase
* make sure disconnected wifi always tries to reconnect
* create explicit class for DoesNotExist, inherit from ModelError?
* explicity check for integrity errors before they happen
* change 'content' directory to symlink to 'client/dist'
* different events for non/alcoholic

