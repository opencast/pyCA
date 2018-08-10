# -*- coding: utf-8 -*-

'''
Tests for database
'''

import unittest
import tempfile
import os

from pyca import db, config


class TestPycaDb(unittest.TestCase):

    dbfile = None

    def setUp(self):
        cfg = './etc/pyca.conf'
        config.update_configuration(cfg)

        self.fd, self.dbfile = tempfile.mkstemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.dbfile)

    def test_get_session(self):
        assert 'autocommit' in db.get_session().__dict__.keys()

    def test_event_data(self):
        series = u'äöüßÄÖÜ'
        title = u'„xyz“'

        e = db.BaseEvent()
        e.set_data({'series': series, 'title': title})

        # Check data serialization
        data = e.get_data()
        assert data['title'] == title
        assert data['series'] == series

    def test_status(self):
        assert db.Status.str(db.Status.UPCOMING) == 'upcoming'

    def test_event(self):
        e = db.BaseEvent()
        e.uid = 'asd'
        e.start = 123
        e.end = 234
        e.status = db.Status.UPCOMING
        e.set_data({})

        assert str(e) == '<Event(start=123, uid="asd")>'

        e = db.RecordedEvent(e)
        assert e.name() == 'recording-123-asd'
        assert e.status_str() == 'upcoming'
        assert e.serialize()['id'] == 'asd'
        assert e.get_tracks() == []

    def test_servicestate(self):
        s = db.ServiceStates()
        s.type = 0
        s.status = 0
        s = db.ServiceStates(s)

        assert s.type == 0
        assert s.status == 0
