# -*- coding: utf-8 -*-
'''
    pyca.db
    ~~~~¨~~

    Database specification for pyCA
'''

import sys
import json
import os.path
from pyca.config import config
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


class Status():
    '''Event status definitions
    '''
    UPCOMING = 1
    RECORDING = 2
    FAILED_RECORDING = 3
    UPLOADING = 4
    FAILED_UPLOADING = 5
    SUCCESS = 6


# Database Schema Definition
class Event(Base):
    '''Database definition of an artist.'''

    __tablename__ = 'event'

    uid = Column('uid', String(255), nullable=False, primary_key=True)
    start = Column('start', Integer(), primary_key=True)
    end = Column('end', Integer(), nullable=False)
    data = Column('data', LargeBinary(), nullable=False)
    protected = Column('protected', Boolean(), nullable=False, default=False)
    status = Column('status', Integer(), nullable=False,
                    default=Status.UPCOMING)

    def get_data(self):
        '''Load JSON data from event.
        '''
        # Python 3 wants str
        if sys.version_info[0] == 2:
            return json.loads(self.data)
        else:
            return json.loads(self.data.decode('utf8'))

    def set_data(self, data):
        '''Store data as JSON.
        '''
        # Python 3 wants bytes
        if sys.version_info[0] == 2:
            self.data = json.dumps(data)
        else:
            self.data = bytes(json.dumps(data), 'utf-8')

    def name(self):
        '''Returns the filesystem name of this event.
        '''
        return 'recording-%i-%s' % (self.start, self.uid)

    def directory(self):
        '''Returns recording directory of this event.
        '''
        return os.path.join(config()['capture']['directory'], self.name())

    def __repr__(self):
        '''Return a string representation of an artist object.

        :return: String representation of object.
        '''
        return '<Event(start=%i, uid="%s")>' % (self.start, self.uid)

    def serialize(self, expand=0):
        '''Serialize this object as dictionary usable for conversion to JSON.

        :param expand: Defines if sub objects shall be serialized as well.
        :return: Dictionary representing this object.
        '''
        return {'start': self.start,
                'end': self.end,
                'uid': self.uid,
                'data': self.data}
