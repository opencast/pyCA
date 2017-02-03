# -*- coding: utf-8 -*-

'''
Tests for pyCA configuration
'''

import unittest

from pyca import config


class TestPycaConfig(unittest.TestCase):

    def test_check(self):
        config.config()['server']['insecure'] = True
        config.config()['server']['certificate'] = 'xxx'
        config.check()


if __name__ == '__main__':
    unittest.main()
