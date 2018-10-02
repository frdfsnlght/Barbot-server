
from peewee import SqliteDatabase, Model

from .config import config
from .app import app

models = []

db = SqliteDatabase(config.getpath('db', 'dbFile'), pragmas = {
    'journal_mode': 'wal',  # allow readers and writers to co-exist
    'cache_size': 10000,    # 10000 pages, or ~40MB
    'foreign_keys': 1,      # enforce foreign-key constraints
    'ignore_check_constraints' : 0  # enforce CHECK constraints
})

class BarbotModel(Model):
    pass

class ModelError(Exception):
    pass
    
def addModel(cls):
    models.append(cls)
    
@app.before_request
def _connect_db():
    db.connect(reuse_if_open = True)
    return None

@app.after_request
def _close_db(r):
    if not db.is_closed():
        db.close()
    return r

