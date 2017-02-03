# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import json
import shutil
import tempfile
import unittest

from pyca import capture, config, utils
from pyca.db import BaseEvent


class TestPycaCapture(unittest.TestCase):

    def test_start_capture(self):
        # Mock event
        event = BaseEvent()
        event.uid = '123123'
        event.start = utils.timestamp()
        event.end = event.start + 1
        data = [{'data': u'äüÄÜß',
                 'fmttype': 'application/xml',
                 'x-apple-filename': 'episode.xml'},
                {'data': u'event.title=äüÄÜß',
                 'fmttype': 'application/text',
                 'x-apple-filename': 'org.opencastproject.capture.agent' +
                                     '.properties'}]
        event.data = json.dumps({'attach': data}).encode('utf-8')

        # Mock some methods
        capture.http_request = lambda x, y=False: None
        capture.recording_state = lambda x, y=False: None
        capture.register_ca = lambda status=False: None
        capture.update_event_status = lambda x, y=False: None

        config.config()['capture']['directory'] = tempfile.mkdtemp()
        config.config()['service-ingest'] = ['']
        try:
            capture.start_capture(event)
        finally:
            shutil.rmtree(config.config()['capture']['directory'])


if __name__ == '__main__':
    unittest.main()
