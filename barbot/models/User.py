
import logging
from peewee import *
from passlib.context import CryptContext

from ..db import db, BarbotModel, ModelError, addModel
from ..bus import bus


_logger = logging.getLogger('Models.User')

_pwdContext = CryptContext(
    schemes = ['bcrypt'],
    deprecated = 'auto',
)

@bus.on('server/start')
def _bus_serverStart():
    users = User.select()
    if not users:
        _logger.warning('There are no user\'s in the database!')
        user = User.addUser('admin', 'Administrator', None, isAdmin = True)
        _logger.warning('Added "admin" user with empty password! Please set a password ASAP!')
    else:
        admin = User.get_or_none(User.isAdmin == True)
        if not admin:
            _logger.warning('There must be at least one admin user! Please add one!')

class User(BarbotModel):
    name = CharField(unique = True)
    fullName = CharField()
    password = CharField(null = True)
    isAdmin = BooleanField(default = False)
    
    @staticmethod
    def addUser(name, fullName, password = None, isAdmin = False):
        if not name:
            raise ModelError('user name is required')
        if not fullName:
            raise ModelError('user fullName is required')
        user = User()
        user.name = name
        user.fullName = fullName
        user.setPassword(password)
        user.isAdmin = isAdmin
        user.save()
        return user

    @staticmethod
    def deleteUser(name):
        if not name:
            raise ModelError('user name is required')
        user = User.get_or_none(User.name == name)
        if user:
            user.delete_instance()
        else:
            raise ModelError('user not found')
            
    @staticmethod
    def setUserPassword(name, password):
        if not name:
            raise ModelError('user name is required')
        user = User.get_or_none(User.name == name)
        if user:
            user.setPassword(password)
            user.save()
        else:
            raise ModelError('user not found')
            
    @staticmethod
    def authenticate(name, password):
        user = User.get_or_none(User.name == name)
        if user and user.passwordMatches(password):
            return user
        return False
        
    # override
    def save(self, *args, **kwargs):
        if super().save(*args, **kwargs):
            bus.emit('model/user/saved', self)
    
    # override
    def delete_instance(self, *args, **kwargs):
        super().delete_instance(*args, **kwargs)
        bus.emit('model/user/deleted', self)
    
    def setPassword(self, password):
        if password:
            self.password = _pwdContext.hash(password)
        else:
            self.password = None
    
    def passwordMatches(self, password):
        if not password and not self.password:
            return True
        return _pwdContext.verify(password, self.password)
        
    def toDict(self):
        out = {
            'id': self.id,
            'name': self.name,
            'fullName': self.fullName,
            'isAdmin': self.isAdmin,
        }
        return out
        
    
    class Meta:
        database = db
        only_save_dirty = True

addModel(User)
