# -*- coding: utf-8 -*-
'''
    pyca.db
    ~~~~¨~~

    Database specification for pyCA
'''

import json
import os.path
from pyca.config import config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, LargeBinary, create_engine
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
    FINISHED_RECORDING = 4
    UPLOADING = 5
    FAILED_UPLOADING = 6
    FINISHED_UPLOADING = 7

    @classmethod
    def str(cls, status):
        '''Convert status (id) to its string name.'''
        for k, v in cls.__dict__.items():
            if k[0] in 'FRSU' and v == status:
                return k.lower().replace('_', ' ')


# Database Schema Definition
class BaseEvent():
    '''Database definition of an event.'''

    __tablename__ = 'event'

    uid = Column('uid', String(255), nullable=False, primary_key=True)
    start = Column('start', Integer(), primary_key=True)
    end = Column('end', Integer(), nullable=False)
    data = Column('data', LargeBinary(), nullable=False)

    def get_data(self):
        '''Load JSON data from event.
        '''
        return json.loads(self.data.decode('utf-8'))

    def set_data(self, data):
        '''Store data as JSON.
        '''
        # Python 3 wants bytes
        self.data = json.dumps(data).encode('utf-8')

    def name(self):
        '''Returns the filesystem name of this event.
        '''
        return 'recording-%i-%s' % (self.start, self.uid)

    def directory(self):
        '''Returns recording directory of this event.
        '''
        return os.path.join(config()['capture']['directory'], self.name())

    def status_str(self):
        '''Return status as string.
        '''
        return Status.str(self.status)

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


class UpcomingEvent(Base, BaseEvent):
    '''List of upcoming events'''

    __tablename__ = 'upcoming_event'


class RecordedEvent(Base, BaseEvent):
    '''List of events pyca tried to record.'''

    __tablename__ = 'recorded_event'

    status = Column('status', Integer(), nullable=False,
                    default=Status.UPCOMING)
    tracks = Column('tracks', LargeBinary(), nullable=True)

    def __init__(self, event=None):
        if event:
            self.uid = event.uid
            self.start = event.start
            self.end = event.end
            self.data = event.data
            if hasattr(event, 'status'):
                self.status = event.status

    def get_tracks(self):
        '''Load JSON track data from event.
        '''
        if not self.tracks:
            return []
        return json.loads(self.tracks.decode('utf-8'))

    def set_tracks(self, tracks):
        '''Store track data as JSON.
        '''
        self.tracks = json.dumps(tracks).encode('utf-8')
