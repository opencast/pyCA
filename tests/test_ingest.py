# -*- coding: utf-8 -*-

'''
Tests for basic capturing
'''

import os
import os.path
import shutil
import tempfile
import unittest

from unittest.mock import patch

from pyca import ingest, config, db, utils
from tests.tools import should_fail, terminate_fn


class TestPycaIngest(unittest.TestCase):

    def setUp(self):
        ingest.http_request = lambda x, y=False: b'xxx'
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
