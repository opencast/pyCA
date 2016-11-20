# -*- coding: utf-8 -*-

'''
Tests for database
'''

import unittest
import logging
import tempfile
import os
import sys

from pyca import db, config

class TestSequenceFunctions(unittest.TestCase):

    dbfile = None

    def setUp(self):
        cfg = './etc/pyca.conf'
        config.update_configuration(cfg)

        _, self.dbfile = tempfile.mkstemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile

    def tearDown(self):
        os.remove(self.dbfile)

    def test_get_service(self):
        assert 'autocommit' in db.get_session().__dict__.keys()


if __name__ == '__main__':
    unittest.main()
