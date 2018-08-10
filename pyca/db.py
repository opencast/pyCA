# -*- coding: utf-8 -*-
'''
    pyca.db
    ~~~~¨~~

    Database specification for pyCA
'''

import json
import os.path
import string
from pyca.config import config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Text, LargeBinary, create_engine
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


class Constants():

    @classmethod
    def str(cls, value):
        '''Convert status (id) to its string name.'''
        for k, v in cls.__dict__.items():
            if k[0] in string.ascii_uppercase and v == value:
                return k.lower().replace('_', ' ')


class Status(Constants):
    '''Event status definitions
    '''
    UPCOMING = 1
    RECORDING = 2
    FAILED_RECORDING = 3
    FINISHED_RECORDING = 4
    UPLOADING = 5
    FAILED_UPLOADING = 6
    FINISHED_UPLOADING = 7


class ServiceStatus(Constants):
    '''Service status type definitions
    '''
    STOPPED = 1
    IDLE = 2
    BUSY = 3


class Service(Constants):
    '''Service type definitions
    '''
    AGENTSTATE = 1
    CAPTURE = 2
    INGEST = 3
    SCHEDULE = 4


# Database Schema Definition
class BaseEvent():
    '''Database definition of an event.'''

    __tablename__ = 'event'

    uid = Column('uid', Text(), nullable=False, primary_key=True)
    start = Column('start', Integer(), primary_key=True)
    end = Column('end', Integer(), nullable=False)
    title = Column('title', Text())
    data = Column('data', LargeBinary(), nullable=False)
    status = Column('status', Integer(), nullable=False,
                    default=Status.UPCOMING)
    tracks = Column('tracks', LargeBinary(), nullable=True)

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

    def remaining_duration(self, time):
        '''Returns the remaining duration for a recording.
        '''
        return max(0, self.end - max(self.start, time))

    def status_str(self):
        '''Return status as string.
        '''
        return Status.str(self.status)

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

    def __repr__(self):
        '''Return a string representation of an artist object.

        :return: String representation of object.
        '''
        return '<Event(start=%i, uid="%s")>' % (self.start, self.uid)

    def serialize(self):
        '''Serialize this object as dictionary usable for conversion to JSON.

        :return: Dictionary representing this object.
        '''
        return {
            'type': 'event',
            'id': self.uid,
            'attributes': {
                'start': self.start,
                'end': self.end,
                'uid': self.uid,
                'title': self.title,
                'data': self.get_data(),
                'status': Status.str(self.status)
                }
            }


class UpcomingEvent(Base, BaseEvent):
    '''List of upcoming events'''

    __tablename__ = 'upcoming_event'


class RecordedEvent(Base, BaseEvent):
    '''List of events pyca tried to record.'''

    __tablename__ = 'recorded_event'

    def __init__(self, event=None):
        if event:
            self.uid = event.uid
            self.start = event.start
            self.end = event.end
            self.title = event.title
            self.data = event.data
            self.status = event.status


class ServiceStates(Base):
    '''List of internal service states.'''

    __tablename__ = 'service_states'

    type = Column('type', Integer(), nullable=False, primary_key=True)
    status = Column('status', Integer(), nullable=False,
                    default=ServiceStatus.STOPPED)

    def __init__(self, service=None):
        if service:
            self.type = service.type
            self.status = service.status
