# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import unittest
import logging
import tempfile
import shutil
import sys

from pyca import ca, config

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        cfg = './etc/pyca.conf'
        config.update_configuration(cfg)


    def test_capture(self):
        logging.info('Starting test recording (10sec)')
        directory = tempfile.mkdtemp()
        try:
            logging.info('Recording directory: %s', directory)
            logging.info('Created recording directory')
            logging.info('Start recording')
            tracks = ca.recording_command(directory, 'testname', 2)
            logging.info('Finished recording')

            logging.info('Testing Ingest')

            # Set some ingest endpoint
            config.config()['service-ingest'] = ['']
            # Mock http_request method
            ca.http_request = lambda x, y=False: None
            ca.ingest(tracks, directory, '123', 'fast', '')
        finally:
            shutil.rmtree(directory)

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


if __name__ == '__main__':
    unittest.main()
