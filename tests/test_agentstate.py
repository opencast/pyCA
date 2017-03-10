# -*- coding: utf-8 -*-
'''
pyCA tests for the agents state handling
'''

import os
import os.path
import tempfile
import unittest

from pyca import agentstate, config, db, utils
from tests.tools import terminate_fn


class TestPycaAgentState(unittest.TestCase):

    def setUp(self):
        utils.http_request = lambda x, y=False: b'xxx'
        _, self.dbfile = tempfile.mkstemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        config.config()['service-capture.admin'] = ['']

        # Mock event
        db.init()

    def tearDown(self):
        os.remove(self.dbfile)

    def test_run(self):
        agentstate.terminate = terminate_fn(1)
        try:
            agentstate.run()
        except Exception:
            assert False


if __name__ == '__main__':
    unittest.main()
