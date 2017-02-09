# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import os
import shutil
import sys
import tempfile
import unittest

from pyca import capture, config, db, utils

if sys.version_info.major > 2:
    try:
        from importlib import reload
    except ImportError:
        from imp import reload


class TestPycaCapture(unittest.TestCase):

    dbfile = None
    cadir = None
    event = None

    def setUp(self):
        reload(config)
        reload(capture)
        reload(db)
        capture.http_request = lambda x, y=False: b'xxx'
        _, self.dbfile = tempfile.mkstemp()
        self.cadir = tempfile.mkdtemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        config.config()['capture']['command'] = 'touch {{dir}}/{{name}}.mp4'
        config.config()['capture']['directory'] = self.cadir
        config.config()['service-ingest'] = ['']
        config.config()['service-capture.admin'] = ['']

        # Mock event

        db.init()
        self.event = db.BaseEvent()
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

    def tearDown(self):
        os.remove(self.dbfile)
        shutil.rmtree(self.cadir)

    def test_start_capture(self):
        assert capture.start_capture(self.event)

    def test_start_capture_recording_command_failure(self):
        config.config()['capture']['command'] = 'false'
        assert not capture.start_capture(self.event)

    def test_start_capture_ingest_failure(self):
        capture.ingest = 'fail'
        assert not capture.start_capture(self.event)

    def test_register_ca(self):
        assert capture.register_ca()
        capture.http_request = 'fail'
        assert not capture.register_ca()
        config.config()['agent']['backup_mode'] = True
        assert capture.register_ca()

    def test_recording_state(self):
        config.config()['service-capture.admin'] = ['']
        capture.recording_state('123', 'recording')
        capture.http_request = 'fail'
        capture.recording_state('123', 'recording')
        config.config()['agent']['backup_mode'] = True
        capture.recording_state('123', 'recording')

    def test_safe_start_capture(self):
        capture.start_capture = 'fail'
        assert not capture.safe_start_capture(1)
        capture.start_capture = lambda x: True
        assert capture.safe_start_capture(1)

    def test_control_loop(self):
        capture.control_loop = lambda: True
        capture.run()


if __name__ == '__main__':
    unittest.main()
