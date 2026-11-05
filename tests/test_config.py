# -*- coding: utf-8 -*-

'''
Tests for pyCA configuration
'''

import os
import tempfile
import unittest

from pyca import config
from tests.tools import reload


class TestPycaConfig(unittest.TestCase):

    def test_check(self):
        config.config()['server']['insecure'] = True
        config.config()['server']['certificate'] = '/xxx'
        with self.assertRaises(IOError):
            config.check()

    def _load(self, agent_section):
        '''Load a configuration with the given [agent] section.'''
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        self.addCleanup(reload, config)
        with os.fdopen(fd, 'w') as cfgfile:
            cfgfile.write('[agent]\n%s\n[capture]\n' % agent_section)
            cfgfile.write("flavors = 'presenter/source', "
                          "'presentation/source'\n")
            cfgfile.write("files = 'a', 'b'\n")
        return config.update_configuration(path)

    def test_inputs(self):
        self.assertEqual(self._load('')['agent']['inputs'], [])
        self.assertEqual(self._load('inputs = ')['agent']['inputs'], [])
        self.assertEqual(self._load("inputs = ''")['agent']['inputs'], [])
        self.assertEqual(
            self._load("inputs = 'presentation/source'")['agent']['inputs'],
            ['presentation/source'])
        self.assertEqual(
            self._load("inputs = 'presenter/source', 'presentation/source'")
            ['agent']['inputs'],
            ['presenter/source', 'presentation/source'])

    def test_inputs_must_be_capture_flavors(self):
        with self.assertRaises(ValueError) as e:
            self._load("inputs = 'presenter/source', 'other/source'")
        self.assertIn('other/source', str(e.exception))

    def test_inputs_length(self):
        with self.assertRaises(ValueError):
            self._load("inputs = '%s'" % ('x' * 257))

