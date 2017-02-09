# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import unittest

from pyca import utils, config
import sys
if sys.version_info.major > 2:
    try:
        from importlib import reload
    except ImportError:
        from imp import reload


class TestPycaUtils(unittest.TestCase):

    def setUp(self):
        reload(utils)

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
        utils.http_request = lambda x, y=False: res
        endpoint = u'https://octestallinone.virtuos.uos.de/capture-admin'
        assert utils.get_service('') == [endpoint]

    def test_ensurelist(self):
        assert utils.ensurelist(1) == [1]
        assert utils.ensurelist([1]) == [1]

    def test_configure_service(self):
        utils.get_service = lambda x: 'x'
        utils.configure_service('x')
        assert config.config()['service-x'] == 'x'

    def test_http_request(self):
        config.config()['server']['insecure'] = True
        try:
            utils.http_request('http://127.0.0.1:8', [('x', 'y')])
        except Exception as e:
            assert e.args[0] == 7  # connection error


if __name__ == '__main__':
    unittest.main()
