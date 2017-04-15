# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import os
import os.path
import shutil
import tempfile
import unittest

from pyca import capture, config, db, utils
from tests.tools import should_fail, terminate_fn, reload


class TestPycaCapture(unittest.TestCase):

    def setUp(self):
        utils.http_request = lambda x, y=False: b'xxx'
        self.fd, self.dbfile = tempfile.mkstemp()
        self.cadir = tempfile.mkdtemp()
        preview = os.path.join(self.cadir, 'preview.png')
        open(preview, 'a').close()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        config.config()['capture']['command'] = 'touch {{dir}}/{{name}}.mp4'
        config.config()['capture']['directory'] = self.cadir
        config.config()['capture']['preview'] = [preview]
        config.config()['service-capture.admin'] = ['']

        # Mock event
        db.init()
        self.event = db.BaseEvent()
        self.event.uid = '123123'
        self.event.title = u'äüÄÜß'
        self.event.start = utils.timestamp()
        self.event.end = self.event.start
        self.event.status = db.Status.UPCOMING
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
        os.close(self.fd)
        os.remove(self.dbfile)
        shutil.rmtree(self.cadir)
        reload(capture)
        reload(config)
        reload(utils)

    def test_start_capture(self):
        capture.start_capture(self.event)

    def test_start_capture_recording_command_failure(self):
        config.config()['capture']['command'] = 'false'
        try:
            capture.start_capture(self.event)
            assert False
        except RuntimeError:
            assert True

    def test_start_capture_sigterm(self):
        config.config()['capture']['command'] = 'sleep 10'
        config.config()['capture']['sigterm_time'] = 0
        capture.start_capture(self.event)

    def test_start_capture_sigkill(self):
        config.config()['capture']['command'] = 'sleep 10'
        config.config()['capture']['sigkill_time'] = 0
        capture.start_capture(self.event)

    def test_safe_start_capture(self):
        '''Ensure that safe_start_capture always returns without error to not
        disrupt the main loop.
        '''
        capture.start_capture = should_fail
        capture.safe_start_capture(self.event)

    def test_run(self):
        capture.terminate = terminate_fn(1)
        capture.run()

    def test_sigterm(self):
        try:
            capture.sigterm_handler(0, 0)
        except BaseException as e:
            assert e.code == 0
            assert utils.terminate()
