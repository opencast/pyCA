# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import json
import shutil
import tempfile
import unittest

from pyca import ca, config
from pyca.db import Event


class TestSequenceFunctions(unittest.TestCase):

    def test_get_service(self):
        res = '''{"services":{
                    "service":{
                        "type":"org.opencastproject.capture.admin",
                        "host":"https:\/\/octestallinone.virtuos.uos.de",
                        "path":"\/capture-admin",
                        "active":true,
                        "online":true,
                        "maintenance":false,
                        "jobproducer":false,
                        "onlinefrom":"2016-11-20T02:01:03.525+01:00",
                        "service_state":"NORMAL",
                        "state_changed":"2016-11-20T02:01:03.525+01:00",
                        "error_state_trigger":0,
                        "warning_state_trigger":0}}}'''.encode('utf-8')
        # Mock http_request method
        ca.http_request = lambda x, y=False: res
        endpoint = u'https://octestallinone.virtuos.uos.de/capture-admin'
        assert ca.get_service('') == [endpoint]

    def test_start_capture(self):
        # Mock event
        event = Event()
        event.uid = '123123'
        event.start = ca.get_timestamp()
        event.end = event.start + 1
        data = [{'data': u'äüÄÜß',
                 'fmttype': 'application/xml',
                 'x-apple-filename': 'episode.xml'},
                {'data': u'event.title=äüÄÜß',
                 'fmttype': 'application/text',
                 'x-apple-filename': 'org.opencastproject.capture.agent'
                                     + '.properties'}]
        event.data = json.dumps({'attach': data}).encode('utf-8')

        # Mock some methods
        ca.http_request = lambda x, y=False: None
        ca.recording_state = lambda x, y=False: None
        ca.register_ca = lambda status=False: None
        ca.update_event_status = lambda x, y=False: None

        config.config()['capture']['directory'] = tempfile.mkdtemp()
        config.config()['service-ingest'] = ['']
        try:
            ca.start_capture(event)
        finally:
            shutil.rmtree(config.config()['capture']['directory'])


if __name__ == '__main__':
    unittest.main()
