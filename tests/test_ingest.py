# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import os
import os.path
import shutil
import tempfile
import unittest

from pyca import ingest, config, db, utils
from tests.tools import should_fail, terminate_fn, reload


class TestPycaIngest(unittest.TestCase):

    def setUp(self):
        utils.http_request = lambda x, y=False: b'xxx'
        ingest.http_request = lambda x, y=False: b'xxx'
        self.fd, self.dbfile = tempfile.mkstemp()
        self.cadir = tempfile.mkdtemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        config.config()['capture']['directory'] = self.cadir
        config.config()['service-ingest'] = ['']
        config.config()['service-capture.admin'] = ['']

        # Mock event
        db.init()
        self.event = db.RecordedEvent()
        self.event.uid = '123123'
        self.event.start = utils.timestamp()
        self.event.end = self.event.start + 1
        data = [{'data': u'äüÄÜß',
                 'fmttype': 'application/xml',
                 'x-apple-filename': 'episode.xml'},
                {'data': u'äüÄÜß',
                 'fmttype': 'application/xml',
                 'x-apple-filename': 'series.xml'},
                {'data': u'event.title=äüÄÜß\n' +
                         u'org.opencastproject.workflow.config.x=123\n' +
                         u'org.opencastproject.workflow.definition=fast',
                 'fmttype': 'application/text',
                 'x-apple-filename': 'org.opencastproject.capture.agent' +
                                     '.properties'}]
        self.event.set_data({'attach': data})

        # Create recording
        os.mkdir(self.event.directory())
        trackfile = os.path.join(self.event.directory(), 'test.mp4')
        with open(trackfile, 'wb') as f:
            f.write(b'123')
        self.event.set_tracks([('presenter/source', trackfile)])

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.dbfile)
        shutil.rmtree(self.cadir)
        reload(ingest)
        reload(utils)

    def test_start_ingest(self):
        assert ingest.start_ingest(self.event)

    def test_start_ingest_failure(self):
        ingest.ingest = should_fail
        assert not ingest.start_ingest(self.event)

    def test_safe_start_ingest(self):
        ingest.start_ingest = should_fail
        assert not ingest.safe_start_ingest(1)
        ingest.start_ingest = lambda x: True
        assert ingest.safe_start_ingest(1)

    def test_run(self):
        ingest.terminate(True)
        ingest.run()
        ingest.terminate = terminate_fn(1)
        ingest.run()
