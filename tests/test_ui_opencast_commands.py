# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import unittest

from pyca.ui import opencast_commands


class TestPycaIngest(unittest.TestCase):

    def setUp(self):
        opencast_commands.http_request = lambda x, y=False, timeout=0: b'xxx'
        opencast_commands.service = lambda x, force_update=False: ['']

    def test_schedule_defaults(self):
        opencast_commands.schedule()
