# -*- coding: utf-8 -*-
'''
    pyca.db
    ~~~~¨~~

    Database specification for pyCA
'''

import json
from config import config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Boolean, Integer, String, LargeBinary
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
Base = declarative_base()


def init():
    '''Initialize connection to database. Additionally the basic database
    structure will be created if nonexistent.
    '''
    global engine
    engine = create_engine(config()['agent']['database'])
    Base.metadata.create_all(engine)


def get_session():
    '''Get a session for database communication. If necessary a new connection
    to the database will be established.

    :return:  Database session
    '''
    if 'engine' not in globals():
        init()
    Session = sessionmaker(bind=engine)
    return Session()


# Database Schema Definition
class Event(Base):
    '''Database definition of an artist.'''

    __tablename__ = 'event'

    start = Column('start', Integer(), primary_key=True)
    end = Column('end', Integer(), nullable=False)
    uid = Column('uid', String(255), nullable=False)
    data = Column('data', LargeBinary(), nullable=False)
    protected = Column('protected', Boolean(), nullable=False, default=False)

    def get_data(self):
        return json.loads(self.data)

    def set_data(self, data):
        self.data = json.dumps(data)

    def __repr__(self):
        '''Return a string representation of an artist object.

        :return: String representation of object.
        '''
        return '<Build(id=%i, name="%s")>' % (self.start, self.end)

    def serialize(self, expand=0):
        '''Serialize this object as dictionary usable for conversion to JSON.

        :param expand: Defines if sub objects shall be serialized as well.
        :return: Dictionary representing this object.
        '''
        return {'start': self.start,
                'end': self.end,
                'uid': self.uid,
                'data': self.data}
