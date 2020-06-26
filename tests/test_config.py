# -*- coding: utf-8 -*-

'''
Tests for pyCA configuration
'''

import unittest

from pyca import config


class TestPycaConfig(unittest.TestCase):

    def test_check(self):
        config.config()['server']['insecure'] = True
        config.config()['server']['certificate'] = '/xxx'
        with self.assertRaises(IOError):
            config.check()
