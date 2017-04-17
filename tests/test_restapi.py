# -*- coding: utf-8 -*-
'''
pyCA tests for the REST api.
'''

import json
import os
import os.path
import tempfile
import unittest

from pyca import ui, config, db


class TestPycaRestInterface(unittest.TestCase):

    auth = {'Authorization': 'Basic YWRtaW46b3BlbmNhc3Q='}

    def setUp(self):
        self.fd1, self.dbfile = tempfile.mkstemp()
        config.config()['agent']['database'] = 'sqlite:///' + self.dbfile
        db.init()

    def tearDown(self):
        os.close(self.fd1)
        os.remove(self.dbfile)

    def add_test_event(self):
        event = db.RecordedEvent()
        event.uid = '123'
        event.start = 1
        event.end = 2
        event.set_data('')
        event.status = db.Status.FINISHED_UPLOADING
        session = db.get_session()
        session.add(event)
        session.commit()
        return event

    def test_servicestatus(self):
        # Without authentication
        with ui.app.test_request_context():
            assert ui.jsonapi.internal_state().status_code == 401

        # With authentication
        with ui.app.test_request_context(headers=self.auth):
            response = ui.jsonapi.internal_state()
            assert response.status_code == 200
            services = json.loads(response.data.decode('utf-8'))
            for service, status in services.items():
                assert hasattr(db.Service, service.upper())
                assert status == db.ServiceStatus.str(db.ServiceStatus.STOPPED)

    def test_events(self):
        # Without authentication
        with ui.app.test_request_context():
            assert ui.jsonapi.events().status_code == 401

        # With authentication
        with ui.app.test_request_context(headers=self.auth):
            response = ui.jsonapi.events()
            assert response.status_code == 200
            assert json.loads(response.data.decode('utf-8')) == []

        # With authentication and event
        event = self.add_test_event()
        with ui.app.test_request_context(headers=self.auth):
            response = ui.jsonapi.events()
            assert response.status_code == 200
            events = json.loads(response.data.decode('utf-8'))
            assert events[0].get('uid') == event.uid

    def test_event(self):
        # Without authentication
        with ui.app.test_request_context():
            assert ui.jsonapi.event().status_code == 401

        # With authentication but invalid uid
        with ui.app.test_request_context(headers=self.auth):
            response = ui.jsonapi.event('123')
            assert response.status_code == 404
            error = json.loads(response.data.decode('utf-8'))
            assert error == 'No event with specified uid'

        # With authentication and valid uid
        event = self.add_test_event()
        with ui.app.test_request_context(headers=self.auth):
            response = ui.jsonapi.event(event.uid)
            assert response.status_code == 200
            jsonevent = json.loads(response.data.decode('utf-8'))
            assert jsonevent.get('uid') == event.uid

    def test_delete_event(self):
        # Without authentication
        with ui.app.test_request_context():
            assert ui.jsonapi.delete_event().status_code == 401

        # With authentication but invalid uid
        with ui.app.test_request_context(headers=self.auth):
            response = ui.jsonapi.delete_event('')
            assert response.status_code == 404
            error = json.loads(response.data.decode('utf-8'))
            assert error == 'No event with specified uid'

        # With authentication and valid uid
        event = self.add_test_event()
        with ui.app.test_request_context(headers=self.auth):
            response = ui.jsonapi.delete_event(event.uid)
            assert response.status_code == 204
            assert not response.data

    def test_modify_event(self):
        # Without authentication
        with ui.app.test_request_context():
            assert ui.jsonapi.modify_event().status_code == 401

        args = dict(headers=self.auth, content_type='application/json')

        # With authentication but no or invalid data
        for data in (None, '{"invalid":0}', '{"status":"invalid"}'):
            args['data'] = data
            with ui.app.test_request_context(**args):
                response = ui.jsonapi.modify_event('')
                assert response.status_code == 400
                error = json.loads(response.data.decode('utf-8'))
                assert error == 'Invalid data'

        # With authentication but invalid uid
        args['data'] = json.dumps(dict(start=1000, end=2000))
        with ui.app.test_request_context(**args):
            response = ui.jsonapi.modify_event('')
            assert response.status_code == 404
            error = json.loads(response.data.decode('utf-8'))
            assert error == 'No event with specified uid'

        # With authentication and valid uid
        event = self.add_test_event()
        with ui.app.test_request_context(**args):
            response = ui.jsonapi.modify_event(event.uid)
            assert response.status_code == 200
            jsonevent = json.loads(response.data.decode('utf-8'))
            assert jsonevent.get('uid') == event.uid
            assert jsonevent.get('start') == 1000
            assert jsonevent.get('end') == 2000
