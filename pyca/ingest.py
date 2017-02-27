# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import http_request, configure_service, set_service_status
from pyca.utils import recording_state, update_event_status, terminate
from pyca.config import config
from pyca.db import get_session, RecordedEvent, Status, Service, ServiceStatus
import logging
import os
import os.path
import pycurl
from random import randrange
import time
import traceback


def get_config_params(properties):
    '''Extract the set of configuration parameters from the properties attached
    to the schedule
    '''
    param = []
    wdef = ''
    for prop in properties.split('\n'):
        if prop.startswith('org.opencastproject.workflow.config'):
            key, val = prop.split('=', 1)
            key = key.split('.')[-1]
            param.append((key, val))
        elif prop.startswith('org.opencastproject.workflow.definition'):
            wdef = prop.split('=', 1)[-1]
    return wdef, param


def start_ingest(event):

    # Put metadata files on disk
    attachments = event.get_data().get('attach')
    workflow_config = ''
    for attachment in attachments:
        value = attachment.get('data')
        if attachment.get('fmttype') == 'application/text':
            workflow_def, workflow_config = get_config_params(value)
        filename = attachment.get('x-apple-filename')
        with open(os.path.join(event.directory(), filename), 'wb') as f:
            f.write(value.encode('utf-8'))

    # If we are a backup CA, we don't want to actually upload anything. So
    # let's just quit here.
    if config()['agent']['backup_mode']:
        return True

    # Upload everything
    set_service_status(Service.INGEST, ServiceStatus.BUSY)
    recording_state(event.uid, 'uploading')
    update_event_status(event, Status.UPLOADING)

    try:
        ingest(event.get_tracks(), event.directory(), event.uid, workflow_def,
               workflow_config)
    except:
        logging.error('Something went wrong during the upload')
        logging.error(traceback.format_exc())
        # Update state if something went wrong
        recording_state(event.uid, 'upload_error')
        update_event_status(event, Status.FAILED_UPLOADING)
        set_service_status(Service.INGEST, ServiceStatus.IDLE)
        return False

    # Update state
    recording_state(event.uid, 'upload_finished')
    update_event_status(event, Status.FINISHED_UPLOADING)
    set_service_status(Service.INGEST, ServiceStatus.IDLE)
    return True


def ingest(tracks, recording_dir, recording_id, workflow_def,
           workflow_config):
    '''Ingest a finished recording to the Matterhorn server.
    '''

    # select ingest service
    # The ingest service to use is selected at random from the available
    # ingest services to ensure that not every capture agent uses the same
    # service at the same time
    service = config()['service-ingest']
    service = service[randrange(0, len(service))]
    logging.info('Selecting ingest service to use: ' + service)

    # create mediapackage
    logging.info('Creating new mediapackage')
    mediapackage = http_request(service + '/createMediaPackage')

    # add episode DublinCore catalog
    if os.path.isfile('%s/episode.xml' % recording_dir):
        logging.info('Adding episode DC catalog')
        dublincore = ''
        with open('%s/episode.xml' % recording_dir, 'rb') as episodefile:
            dublincore = episodefile.read().decode('utf8')
        fields = [('mediaPackage', mediapackage),
                  ('flavor', 'dublincore/episode'),
                  ('dublinCore', dublincore)]
        mediapackage = http_request(service + '/addDCCatalog', fields)

    # add series DublinCore catalog
    if os.path.isfile('%s/series.xml' % recording_dir):
        logging.info('Adding series DC catalog')
        dublincore = ''
        with open('%s/series.xml' % recording_dir, 'rb') as seriesfile:
            dublincore = seriesfile.read().decode('utf8')
        fields = [('mediaPackage', mediapackage),
                  ('flavor', 'dublincore/series'),
                  ('dublinCore', dublincore)]
        mediapackage = http_request(service + '/addDCCatalog', fields)

    # add track
    for (flavor, track) in tracks:
        logging.info('Adding track ({0} -> {1})'.format(flavor, track))
        track = track.encode('ascii', 'ignore')
        fields = [('mediaPackage', mediapackage), ('flavor', flavor),
                  ('BODY1', (pycurl.FORM_FILE, track))]
        mediapackage = http_request(service + '/addTrack', fields)

    # ingest
    logging.info('Ingest recording')
    fields = [('mediaPackage', mediapackage)]
    if workflow_def:
        fields.append(('workflowDefinitionId', workflow_def))
    if recording_id:
        fields.append(('workflowInstanceId',
                       recording_id.encode('ascii', 'ignore')))
    fields += workflow_config
    mediapackage = http_request(service + '/ingest', fields)


def safe_start_ingest(event):
    '''Start a capture process but make sure to catch any errors during this
    process, log them but otherwise ignore them.
    '''
    try:
        return start_ingest(event)
    except Exception:
        logging.error('Start ingest failed')
        logging.error(traceback.format_exc())
        set_service_status(Service.INGEST, ServiceStatus.IDLE)
        return False


def control_loop():
    '''Main loop of the capture agent, retrieving and checking the schedule as
    well as starting the capture process if necessry.
    '''
    set_service_status(Service.INGEST, ServiceStatus.IDLE)
    while not terminate():
        # Get next recording
        events = get_session().query(RecordedEvent)\
                              .filter(RecordedEvent.status ==
                                      Status.FINISHED_RECORDING)
        if events.count():
            safe_start_ingest(events[0])
        time.sleep(1.0)
    logging.info('Shutting down ingest service')
    set_service_status(Service.INGEST, ServiceStatus.STOPPED)


def run():
    '''Start the capture agent.
    '''
    configure_service('ingest')
    configure_service('capture.admin')
    control_loop()
