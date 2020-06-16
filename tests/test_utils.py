# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import os
import tempfile
import unittest

from pyca import utils, config, db
from tests.tools import should_fail, CurlMock, reload


class TestPycaUtils(unittest.TestCase):

    def setUp(self):
        config.config()['services']['org.opencastproject.capture.admin'] = ['']

        # db
        self.fd, self.dbfile = tempfile.mkstemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        db.init()

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.dbfile)
        reload(utils)
        reload(config)

    def test_get_service(self):
        res = '''{"services":{
                    "service":{
                        "type":"org.opencastproject.capture.admin",
                        "host":"https://octestallinone.virtuos.uos.de",
                        "path":"/capture-admin",
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
        utils.http_request = lambda x, y=False: res
        endpoint = u'https://octestallinone.virtuos.uos.de/capture-admin'
        self.assertEqual(utils.get_service(''), [endpoint])

    def test_ensurelist(self):
        self.assertEqual(utils.ensurelist(1), [1])
        self.assertEqual(utils.ensurelist([1]), [1])

    def test_service(self):
        utils.terminate(False)
        utils.get_service = lambda x: 'x'
        self.assertEqual(utils.service('x'), 'x')

    def test_http_request(self):
        config.config()['server']['insecure'] = True
        config.config()['server']['certificate'] = 'nowhere'
        with self.assertRaises(Exception) as e:
            utils.http_request('http://127.0.0.1:8', [('x', 'y')])
        self.assertEqual(e.exception.args[0], 7)

    def test_http_request_mocked_curl(self):
        config.config()['server']['insecure'] = True
        config.config()['server']['certificate'] = 'nowhere'
        utils.pycurl.Curl = CurlMock
        try:
            utils.http_request('http://127.0.0.1:8', [('x', 'y')])
        except Exception:
            self.fail()
        reload(utils.pycurl)

    def test_register_ca(self):
        utils.http_request = lambda x, y=False: b'xxx'
        utils.register_ca()
        utils.http_request = should_fail
        utils.register_ca()
        config.config()['agent']['backup_mode'] = True
        utils.register_ca()

    def test_recording_state(self):
        utils.http_request = lambda x, y=False: b''
        utils.recording_state('123', 'recording')
        utils.http_request = should_fail
        utils.recording_state('123', 'recording')
        config.config()['agent']['backup_mode'] = True
        utils.recording_state('123', 'recording')

    def test_set_service_status_immediate(self):
        utils.http_request = lambda x, y=False: b''
        utils.set_service_status_immediate(db.Service.SCHEDULE,
                                           db.ServiceStatus.IDLE)
        utils.set_service_status_immediate(db.Service.INGEST,
                                           db.ServiceStatus.BUSY)
        utils.set_service_status_immediate(db.Service.CAPTURE,
                                           db.ServiceStatus.BUSY)
