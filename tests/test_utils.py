# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import unittest

from pyca import utils


class TestPycaUtils(unittest.TestCase):

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


if __name__ == '__main__':
    unittest.main()
