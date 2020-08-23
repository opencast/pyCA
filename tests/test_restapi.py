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

    content_type = 'application/vnd.api+json'
    headers = {
        'Authorization': 'Basic YWRtaW46b3BlbmNhc3Q=',
        'Content-Type': content_type
    }

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
        return db.RecordedEvent(event)

    def test_images(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.get_images().status_code, 401)

        config.config()['capture']['preview_dir'] = '/tmp'

        # With authentication
        for preview, response_len in (([], 0), ([__file__], 1)):
            config.config()['capture']['preview'] = preview
            with ui.app.test_request_context(headers=self.headers):
                response = ui.jsonapi.get_images()
                self.assertEqual(
                    response.headers['Content-Type'], self.content_type)
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data.decode('utf-8'))
                self.assertEqual(len(data['data']), response_len)

    def test_name(self):
        config.config()['agent']['name'] = 'a'

        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.get_name().status_code, 401)

        # With authentication
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.get_name()
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data.decode('utf-8'))
            self.assertEqual(data['meta']['name'], 'a')

    def test_logs(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.logs().status_code, 401)

        # With authentication but without command
        with ui.app.test_request_context(headers=self.headers):
            self.assertEqual(ui.jsonapi.logs().status_code, 404)

        config.config()['ui']['log_command'] = 'echo test'

        # With authentication
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.logs()
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data.decode('utf-8'))
            self.assertEqual(len(data['data']), 1)
            self.assertEqual(data['data'][0]['attributes']['lines'], ['test'])

    def test_metrics(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.metrics().status_code, 401)

        # With authentication
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.metrics()
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            self.assertEqual(response.status_code, 200)
            keys = json.loads(response.data.decode('utf-8'))['meta'].keys()
            expect = {'disk_usage_in_bytes', 'load', 'memory_usage_in_bytes',
                      'services', 'upstream'}
            self.assertEqual(set(keys), expect)

    def test_mediatype_param(self):
        # JSONAPI must respond with 415 when mediatype parameters are present
        param_headers = self.headers.copy()
        param_headers['Content-Type'] = self.headers['Content-Type'] + ' a=b;'
        with ui.app.test_request_context(headers=param_headers, method='PUT'):
            self.assertEqual(ui.jsonapi.internal_state().status_code, 415)
            self.assertEqual(ui.jsonapi.events().status_code, 415)
            self.assertEqual(ui.jsonapi.event().status_code, 415)
            self.assertEqual(ui.jsonapi.delete_event().status_code, 415)
            self.assertEqual(ui.jsonapi.modify_event().status_code, 415)

    def test_servicestatus(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.internal_state().status_code, 401)

        # With authentication
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.internal_state()
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            self.assertEqual(response.status_code, 200)
            meta = json.loads(response.data.decode('utf-8'))['meta']
            for service, status in meta['services'].items():
                self.assertTrue(hasattr(db.Service, service.upper()))
                self.assertEqual(status, db.ServiceStatus.str(
                    db.ServiceStatus.STOPPED))

    def test_events(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.events().status_code, 401)

        # With authentication
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.events()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            self.assertEqual(json.loads(
                response.data.decode('utf-8')), dict(data=[]))

        # With authentication and event
        event = self.add_test_event()
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.events()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            events = json.loads(response.data.decode('utf-8'))['data'][0]
            self.assertEqual(events.get('id'), event.uid)

    def test_event(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.event().status_code, 401)

        # With authentication but invalid uid
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.event('123')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            error = json.loads(response.data.decode('utf-8'))['errors'][0]
            self.assertEqual(error, dict(title='No event with specified uid',
                                         status=404))

        # With authentication and valid uid
        event = self.add_test_event()
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.event(event.uid)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            events = json.loads(response.data.decode('utf-8'))['data'][0]
            self.assertEqual(events.get('id'), event.uid)

    def test_delete_event(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.delete_event().status_code, 401)

        # With authentication but invalid uid
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.delete_event('')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            error = json.loads(response.data.decode('utf-8'))['errors'][0]
            self.assertEqual(error, dict(title='No event with specified uid',
                                         status=404))

        # With authentication and valid uid
        event = self.add_test_event()
        with ui.app.test_request_context(headers=self.headers):
            response = ui.jsonapi.delete_event(event.uid)
            self.assertEqual(response.status_code, 204)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            self.assertFalse(response.data)

        # With hard deletion
        event = self.add_test_event()
        directory = event.directory()
        # create a stub recording directory
        if not os.path.exists(directory):
            os.makedirs(directory)
        with ui.app.test_request_context(headers=self.headers,
                                         query_string='hard=true'):
            response = ui.jsonapi.delete_event(event.uid)
            self.assertEqual(response.status_code, 204)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            self.assertFalse(response.data)
            self.assertFalse(os.path.exists(directory))

    def test_modify_event(self):
        # Without authentication
        with ui.app.test_request_context():
            self.assertEqual(ui.jsonapi.modify_event().status_code, 401)

        args = dict(headers=self.headers)

        # With authentication but no or invalid data
        for data in (None,
                     '{"type":"event","id":0,"attributes":{"invalid":0}}',
                     '{"type":"event","id":0,"attributes":\
                     {"status":"invalid"}}'):
            args['data'] = {'data': [data]}
            with ui.app.test_request_context(**args):
                response = ui.jsonapi.modify_event(0)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.headers['Content-Type'], self.content_type)
                error = json.loads(response.data.decode('utf-8'))['errors'][0]
            self.assertEqual(error, dict(title='Invalid data', status=400))

        # With authentication but invalid uid
        content = {
            'data': [{
                'type': 'event',
                'id': 'invalid',
                'attributes': {
                    'start': 1000,
                    'end': 2000
                }
            }]
        }
        args['data'] = json.dumps(content)
        with ui.app.test_request_context(**args):
            response = ui.jsonapi.modify_event('')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            error = json.loads(response.data.decode('utf-8'))['errors'][0]
            self.assertEqual(error, dict(title='Invalid data', status=400))

        # With authentication and valid uid
        event = self.add_test_event()
        content['data'][0]['id'] = event.uid
        args['data'] = json.dumps(content)
        with ui.app.test_request_context(**args):
            response = ui.jsonapi.modify_event(event.uid)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers['Content-Type'], self.content_type)
            jsonevent = json.loads(response.data.decode('utf-8'))['data'][0]
            self.assertEqual(jsonevent.get('id'), event.uid)
            self.assertEqual(jsonevent['attributes'].get('start'), 1000)
            self.assertEqual(jsonevent['attributes'].get('end'), 2000)
