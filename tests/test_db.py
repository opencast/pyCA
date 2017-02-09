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

        _, self.dbfile = tempfile.mkstemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile

    def tearDown(self):
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


if __name__ == '__main__':
    unittest.main()
