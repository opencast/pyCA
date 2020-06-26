# -*- coding: utf-8 -*-
'''
pyCA tests for schedule handling
'''

import os
import os.path
import tempfile
import unittest

from pyca import ui, config, db


class TestPycaUI(unittest.TestCase):

    auth = {'Authorization': 'Basic YWRtaW46b3BlbmNhc3Q='}

    def setUp(self):
        self.fd1, self.dbfile = tempfile.mkstemp()
        self.fd2, self.previewfile = tempfile.mkstemp()
        config.config()['capture']['preview'] = [self.previewfile]
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        db.init()

    def tearDown(self):
        os.close(self.fd1)
        os.close(self.fd2)
        os.remove(self.dbfile)
        os.remove(self.previewfile)

    def test_home(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.home().status_code, 401)

        # With authentication
        with ui.app.test_request_context(headers=self.auth):
            self.assertEqual(ui.home().status_code, 302)

    def test_ui(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.serve_image(0).status_code, 401)

        # With authentication
        with ui.app.test_request_context(headers=self.auth):
            self.assertEqual(ui.serve_image(9)[1], 404)
        with ui.app.test_request_context(headers=self.auth):
            r = ui.serve_image(0)
            self.assertEqual(r.status_code, 200)
            r.close()
