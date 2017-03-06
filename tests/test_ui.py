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
        _, self.dbfile = tempfile.mkstemp()
        _, self.previewfile = tempfile.mkstemp()
        config.config()['capture']['preview'] = [self.previewfile]
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        db.init()

    def tearDown(self):
        os.remove(self.dbfile)
        os.remove(self.previewfile)

    def test_dtfmt(self):
        assert ui.dtfmt(1488830224).startswith('2017-03-0')

    def test_home(self):
        # Without authentication
        with ui.app.test_request_context():
            assert ui.home().status_code == 401

        # With authentication
        with ui.app.test_request_context(headers=self.auth):
            assert '<title>pyCA</title>' in ui.home()

        # Mess up limits (fallback to defaults)
        with ui.app.test_request_context('/?limit_upcoming=nan',
                                         headers=self.auth):
            assert '<title>pyCA</title>' in ui.home()

    def test_ui(self):
        # Without authentication
        with ui.app.test_request_context():
            assert ui.serve_image(0).status_code == 401

        # With authentication
        with ui.app.test_request_context(headers=self.auth):
            assert ui.serve_image(9)[1] == 404
        with ui.app.test_request_context(headers=self.auth):
            r = ui.serve_image(0)
            assert r.status_code == 200
            r.close()


if __name__ == '__main__':
    unittest.main()
