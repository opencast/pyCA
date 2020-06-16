# -*- coding: utf-8 -*-
'''
pyCA tests for schedule handling
'''

import datetime
import os
import os.path
import tempfile
import unittest

from pyca import schedule, config, db, utils
from tests.tools import should_fail, ShouldFailException, terminate_fn, reload


class TestPycaCapture(unittest.TestCase):

    END = (datetime.datetime.today() + datetime.timedelta(days=1)).isoformat()

    VCAL = ('''BEGIN:VCALENDAR
        BEGIN:VEVENT
        UID:20170223T171244Z
        SUMMARY:TEST
        DTSTART:20170223T230000Z
        DTEND:%sZ
        ATTACH;FMTTYPE=application/xml;VALUE=BINARY;ENCODING=BASE64;
          X-APPLE-FILENAME=episode.xml:Li4u
        END:VEVENT
        END:VCALENDAR''' % END).replace('\n        ', '\r\n').encode('utf-8')

    def setUp(self):
        utils.http_request = lambda x, y=False: b'xxx'
        self.fd, self.dbfile = tempfile.mkstemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        config.config()['services']['org.opencastproject.scheduler'] = ['']
        config.config()['services']['org.opencastproject.capture.admin'] = ['']

        # Mock event
        db.init()

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.dbfile)
        reload(utils)
        reload(schedule)

    def test_get_schedule(self):
        # Failed request
        schedule.http_request = should_fail
        schedule.get_schedule()
        self.assertEqual(db.get_session().query(db.UpcomingEvent).count(), 0)

        # Failed parsing ical
        schedule.http_request = lambda x: ShouldFailException
        schedule.get_schedule()
        self.assertEqual(db.get_session().query(db.UpcomingEvent).count(), 0)

        # Get schedule
        schedule.http_request = lambda x: self.VCAL
        schedule.get_schedule()
        self.assertGreater(db.get_session().query(db.UpcomingEvent).count(), 0)

    def test_run(self):
        schedule.terminate = terminate_fn(2)
        schedule.run()
