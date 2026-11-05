# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import json
import os
import tempfile
import unittest

from pyca import utils, config, db
from tests.tools import should_fail, CurlMock, reload
from tests.tools import ShouldFailException as ShouldFail


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
        utils.http_request = lambda x, y=False, timeout=0: res
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
        utils.http_request = lambda x, y=False, timeout=0: b'xxx'
        utils.register_ca()
        utils.http_request = should_fail
        utils.register_ca()
        config.config()['agent']['backup_mode'] = True
        utils.register_ca()

    def test_register_ca_requests(self):
        requests = []

        def record(url, post_data=None, timeout=0):
            requests.append((url, post_data))
            return b''

        utils.http_request = record
        config.config()['agent']['name'] = 'my agent'
        config.config()['ui']['url'] = 'http://pyca.example.org:5000'
        utils.register_ca('capturing')

        # State, configuration and the verification of the agent version
        self.assertEqual(len(requests), 3)
        self.assertEqual(requests[2][0],
                         '/agents/my%20agent/configuration.json')
        self.assertIsNone(requests[2][1])

        url, body = requests[0]
        self.assertEqual(url, '/agents/my%20agent')
        self.assertEqual(body, [
            ('address', 'http://pyca.example.org:5000'),
            ('state', 'capturing')])

        url, body = requests[1]
        self.assertEqual(url, '/agents/my%20agent/configuration')
        self.assertEqual([key for key, _ in body], ['configuration'])
        cfg = json.loads(body[0][1])
        for key in ('vendor.name', 'vendor.model', 'vendor.hardware',
                    'vendor.firmware'):
            self.assertTrue(1 <= len(cfg[key]) <= 256, key)
        self.assertEqual(cfg['capture.local.capable'], 'true')
        self.assertEqual(cfg['capture.local.canstartpaused'], 'false')
        self.assertEqual(cfg['capture.stream.capable'], 'false')
        # All values must be strings and no empty optional lists may be sent
        self.assertTrue(all(isinstance(v, str) for v in cfg.values()))
        self.assertFalse(any(k.startswith('capture.device') for k in cfg))

    def test_register_ca_missing_endpoint(self):
        requests = []
        utils.http_request = lambda *args, **kwargs: requests.append(args)
        utils.service = lambda name, force_update=False: []
        with self.assertLogs('pyca.utils', 'WARNING') as logs:
            utils.register_ca()
        self.assertTrue(any('Missing endpoint' in m for m in logs.output))
        self.assertEqual(requests, [])

    def _register_with_version_response(self, response):
        requests = []

        def fake(url, post_data=None, timeout=0):
            requests.append(url)
            if url.endswith('configuration.json'):
                if isinstance(response, Exception):
                    raise response
                return response
            return b''

        utils.http_request = fake
        return requests

    def test_check_agent_version_2x(self):
        body = json.dumps({'properties-response': {'properties': {'item': [
            {'key': 'vendor.name', 'value': 'Opencast'},
            {'key': 'opencast.agent.version', 'value': 2}]}}}).encode()
        requests = self._register_with_version_response(body)
        with self.assertLogs('pyca.utils', 'INFO') as logs:
            utils.register_ca()
        self.assertTrue(any('2.x agent' in m and 'did not' not in m
                            for m in logs.output))
        self.assertFalse(any('WARNING' in m for m in logs.output))
        # Verified once. Later updates must not ask again.
        utils.register_ca()
        self.assertEqual(
            len([r for r in requests if r.endswith('configuration.json')]),
            1)

    def test_check_agent_version_1x(self):
        # Opencast without CA API 2.x support does not report version 2.
        # A single item may also be returned as object instead of list.
        body = json.dumps({'properties-response': {'properties': {'item': {
            'key': 'opencast.agent.version', 'value': 1}}}}).encode()
        self._register_with_version_response(body)
        with self.assertLogs('pyca.utils', 'WARNING') as logs:
            utils.register_ca()
        self.assertTrue(any('did not register' in m for m in logs.output))

    def test_check_agent_version_missing_key(self):
        body = json.dumps({'properties-response': {'properties': {'item': [
            {'key': 'vendor.name', 'value': 'Opencast'}]}}}).encode()
        self._register_with_version_response(body)
        with self.assertLogs('pyca.utils', 'WARNING') as logs:
            utils.register_ca()
        self.assertTrue(any('did not register' in m for m in logs.output))

    def test_check_agent_version_unusable_answer(self):
        # Errors or garbage must neither raise nor count as verified
        for response in (b'not json', b'{}', b'', ShouldFail(None, 0)):
            requests = self._register_with_version_response(response)
            utils._version_checked = False
            utils.register_ca()
            self.assertFalse(utils._version_checked)
            # Retried with the next update
            utils.register_ca()
            self.assertEqual(
                len([r for r in requests
                     if r.endswith('configuration.json')]), 2)

    def test_agent_configuration_vendor_override(self):
        config.config()['agent']['vendor_name'] = 'ACME'
        config.config()['agent']['vendor_model'] = 'Recorder'
        config.config()['agent']['vendor_hardware'] = 'rev B'
        config.config()['agent']['vendor_firmware'] = '1.2.3'
        cfg = utils.agent_configuration()
        self.assertEqual(cfg['vendor.name'], 'ACME')
        self.assertEqual(cfg['vendor.model'], 'Recorder')
        self.assertEqual(cfg['vendor.hardware'], 'rev B')
        self.assertEqual(cfg['vendor.firmware'], '1.2.3')

    def test_recording_state(self):
        utils.http_request = lambda x, y=False, timeout=0: b''
        utils.recording_state('123', 'recording')
        utils.http_request = should_fail
        utils.recording_state('123', 'recording')
        config.config()['agent']['backup_mode'] = True
        utils.recording_state('123', 'recording')

    def test_set_service_status_immediate(self):
        utils.http_request = lambda x, y=False, timeout=0: b''
        utils.set_service_status_immediate(db.Service.SCHEDULE,
                                           db.ServiceStatus.IDLE)
        utils.set_service_status_immediate(db.Service.INGEST,
                                           db.ServiceStatus.BUSY)
        utils.set_service_status_immediate(db.Service.CAPTURE,
                                           db.ServiceStatus.BUSY)
