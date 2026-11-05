# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import os
import os.path
import shutil
import pycurl
import tempfile
import unittest

from unittest.mock import patch

from pyca import ingest, config, db, utils
from tests.tools import should_fail, terminate_fn


class TestPycaIngest(unittest.TestCase):

    def setUp(self):
        ingest.http_request = lambda x, y=False, timeout=0: b'xxx'
        self.fd, self.dbfile = tempfile.mkstemp()
        self.cadir = tempfile.mkdtemp()
        config.config('agent')['database'] = 'sqlite:///' + self.dbfile
        config.config('capture')['directory'] = self.cadir
        config.config()['services']['org.opencastproject.ingest'] = ['']
        config.config()['services']['org.opencastproject.capture.admin'] = ['']

        # Mock event
        db.init()
        event = db.RecordedEvent()
        event.uid = '123123'
        event.status = db.Status.FINISHED_RECORDING
        event.start = utils.timestamp()
        event.end = event.start + 1
        prop = 'org.opencastproject.capture.agent.properties'
        dcns = 'http://www.opencastproject.org/xsd/1.0/dublincore/'
        data = [{'data': u'äü%sÄÜß' % dcns,
                 'fmttype': 'application/xml',
                 'x-apple-filename': 'episode.xml'},
                {'data': u'äü%sÄÜß' % dcns,
                 'fmttype': 'application/xml',
                 'x-apple-filename': 'series.xml'},
                {'data': u'event.title=äüÄÜß\n' +
                         u'org.opencastproject.workflow.config.x=123\n' +
                         u'org.opencastproject.workflow.definition=fast',
                 'fmttype': 'application/text',
                 'x-apple-filename': prop}]
        event.set_data({'attach': data})

        # Create recording
        os.mkdir(event.directory())
        trackfile = os.path.join(event.directory(), 'test.mp4')
        open(trackfile, 'wb').close()
        event.set_tracks([('presenter/source', trackfile)])
        session = db.get_session()
        session.add(event)
        session.commit()
        self.event = db.RecordedEvent(event)

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.dbfile)
        shutil.rmtree(self.cadir)

    @patch(__name__+'.ingest.ingest')
    def test_safe_start_ingest(self, ingest_fn):
        ingest_fn.side_effect = lambda x: None
        ingest.safe_start_ingest(self.event)
        ingest_fn.side_effect = should_fail
        ingest.safe_start_ingest(self.event)

    def test_run(self):
        ingest.terminate(True)
        ingest.run()
        ingest.terminate = terminate_fn(1)
        ingest.run()
        config.config('agent')['backup_mode'] = True
        ingest.run()

    def test_get_config_params(self):
        properties = '\n'.join([
            'org.opencastproject.workflow.config.encode_720p=true',
            'org.opencastproject.workflow.config.cutting=false',
            'org.opencastproject.workflow.definition=fast',
            'org.opencastproject.nonsense=whatever'
            ])
        workflow, parameters = ingest.get_config_params(properties)
        self.assertEqual(workflow, 'fast')
        self.assertEqual(
                set([('encode_720p', 'true'), ('cutting', 'false')]),
                set(parameters))

    PROP = 'org.opencastproject.capture.agent.properties'
    TRACKS = [['presenter/source', 'a.mp4'], ['presentation/source', 'b.mp4']]

    def _offer_inputs(self, inputs):
        config.config('agent')['inputs'] = inputs
        self.addCleanup(config.config('agent').__setitem__, 'inputs', [])

    def _select(self, properties):
        '''Let the event carry the given agent properties.'''
        attach = [{'data': properties, 'fmttype': 'application/text',
                   'x-apple-filename': self.PROP}]
        self.event.set_data({'attach': attach})

    def test_selected_inputs(self):
        self._select('event.title=x\ncapture.device.names='
                     'presenter/source, presentation/source ,\nx=y\n')
        self.assertEqual(ingest.selected_inputs(self.event),
                         ['presenter/source', 'presentation/source'])

    def test_selected_inputs_nothing_selected(self):
        # No agent properties, no key, empty value, no attachments at all
        self.assertIsNone(ingest.selected_inputs(self.event))
        self._select('event.title=x')
        self.assertIsNone(ingest.selected_inputs(self.event))
        self._select('capture.device.names=')
        self.assertIsNone(ingest.selected_inputs(self.event))
        self._select('capture.device.names= , ')
        self.assertIsNone(ingest.selected_inputs(self.event))
        self.event.set_data({})
        self.assertIsNone(ingest.selected_inputs(self.event))

    def test_select_tracks(self):
        self._offer_inputs(['presenter/source', 'presentation/source'])
        self._select('capture.device.names=presentation/source')
        self.assertEqual(ingest.select_tracks(self.event, self.TRACKS),
                         [('presentation/source', 'b.mp4')])
        self._select('capture.device.names=presenter/source,'
                     'presentation/source')
        self.assertEqual(len(ingest.select_tracks(self.event, self.TRACKS)),
                         2)

    def test_select_tracks_all(self):
        # Without selection
        self._offer_inputs(['presenter/source', 'presentation/source'])
        self._select('event.title=x')
        self.assertEqual(ingest.select_tracks(self.event, self.TRACKS),
                         self.TRACKS)
        # Inputs which are not offered cannot have been selected
        self._offer_inputs([])
        self._select('capture.device.names=presentation/source')
        self.assertEqual(ingest.select_tracks(self.event, self.TRACKS),
                         self.TRACKS)

    def test_select_tracks_stale_selection(self):
        # A selection matching nothing must not result in an empty upload
        self._offer_inputs(['presenter/source'])
        self._select('capture.device.names=removed/input')
        with self.assertLogs('pyca.ingest', 'WARNING'):
            self.assertEqual(ingest.select_tracks(self.event, self.TRACKS),
                             self.TRACKS)

    def test_ingest_only_selected_tracks(self):
        self._offer_inputs(['presenter/source', 'presentation/source'])
        self._select('capture.device.names=presentation/source')
        for name in ('a.mp4', 'b.mp4'):
            open(os.path.join(self.event.directory(), name), 'wb').close()
        self.event.set_tracks(
            [[flavor, os.path.join(self.event.directory(), name)]
             for flavor, name in self.TRACKS])

        requests = []

        def fake_request(url, post_data=None, timeout=None):
            requests.append((url, post_data))
            return b'mediapackage'

        with patch.object(ingest, 'http_request', fake_request), \
                patch.object(ingest, 'service', lambda *a, **k: ['http://x']),\
                patch.object(ingest, 'recording_state'), \
                patch.object(ingest, 'set_service_status_immediate'):
            ingest.ingest(self.event)

        added = [dict(fields) for url, fields in requests
                 if url.endswith('/addTrack')]
        self.assertEqual([track['flavor'] for track in added],
                         ['presentation/source'])
        self.assertEqual(added[0]['BODY1'][0], pycurl.FORM_FILE)
        # The recording is still ingested
        self.assertTrue(requests[-1][0].endswith('/ingest'))

