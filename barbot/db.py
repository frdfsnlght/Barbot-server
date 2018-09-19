
from peewee import SqliteDatabase

import barbot.config
from barbot.flaskApp import app

db = SqliteDatabase(barbot.config.config.getpath('db', 'dbFile'), pragmas = {
    'journal_mode': 'wal',  # allow readers and writers to co-exist
    'cache_size': 10000,    # 10000 pages, or ~40MB
    'foreign_keys': 1,      # enforce foreign-key constraints
    'ignore_check_constraints' : 0  # enforce CHECK constraints
})

@app.before_request
def _connect_db():
    db.connect()
    return None

@app.after_request
def _close_db(r):
    if not db.is_closed():
        db.close()
    return r

