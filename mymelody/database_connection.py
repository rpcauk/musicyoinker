import sqlite3
from mymelody.create_db import initialise_db


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DatabaseConnection(metaclass=Singleton):
    def __init__(self):
        # initialise_db("mm.db")
        self.conn = sqlite3.connect("mm.db")
        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()
