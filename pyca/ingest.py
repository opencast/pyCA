# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import http_request, configure_service, set_service_status
from pyca.utils import set_service_status_immediate, recording_state
from pyca.utils import update_event_status, terminate
from pyca.config import config
from pyca.db import get_session, RecordedEvent, Status, Service, ServiceStatus
import logging
import pycurl
from random import randrange
import time
import traceback

logger = logging.getLogger(__name__)


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
    # get attacments for ingest
    attachments = event.get_data().get('attach')

    # If we are a backup CA, we don't want to actually upload anything. So
    # let's just quit here.
    if config()['agent']['backup_mode']:
        return True

    # Upload everything
    set_service_status(Service.INGEST, ServiceStatus.BUSY)
    recording_state(event.uid, 'uploading')
    update_event_status(event, Status.UPLOADING)

    try:
        ingest(event.get_tracks(), event.directory(), event.uid, attachments)
    except:
        logger.error('Something went wrong during the upload')
        logger.error(traceback.format_exc())
        # Update state if something went wrong
        recording_state(event.uid, 'upload_error')
        update_event_status(event, Status.FAILED_UPLOADING)
        set_service_status_immediate(Service.INGEST, ServiceStatus.IDLE)
        return False

    # Update state
    recording_state(event.uid, 'upload_finished')
    update_event_status(event, Status.FINISHED_UPLOADING)
    set_service_status_immediate(Service.INGEST, ServiceStatus.IDLE)
    return True


def ingest(tracks, recording_dir, recording_id, attachments):
    '''Ingest a finished recording to the Opencast server.
    '''

    # select ingest service
    # The ingest service to use is selected at random from the available
    # ingest services to ensure that not every capture agent uses the same
    # service at the same time
    service = config()['service-ingest']
    service = service[randrange(0, len(service))]
    logger.info('Selecting ingest service to use: ' + service)

    # create mediapackage
    logger.info('Creating new mediapackage')
    mediapackage = http_request(service + '/createMediaPackage')

    # extract workflow_def, workflow_config and add DC catalogs
    prop = 'org.opencastproject.capture.agent.properties'
    dcns = 'http://www.opencastproject.org/xsd/1.0/dublincore/'
    for attachment in attachments:
        data = attachment.get('data')
        if attachment.get('x-apple-filename') == prop:
            workflow_def, workflow_config = get_config_params(data)

        # Check for dublincore catalogs
        elif attachment.get('fmttype') == 'application/xml' and dcns in data:
            name = attachment.get('x-apple-filename', '').rsplit('.', 1)[0]
            logger.info('Adding %s DC catalog' % name)
            fields = [('mediaPackage', mediapackage),
                      ('flavor', 'dublincore/%s' % name),
                      ('dublinCore', data)]
            mediapackage = http_request(service + '/addDCCatalog', fields)

    # add track
    for (flavor, track) in tracks:
        logger.info('Adding track ({0} -> {1})'.format(flavor, track))
        track = track.encode('ascii', 'ignore')
        fields = [('mediaPackage', mediapackage), ('flavor', flavor),
                  ('BODY1', (pycurl.FORM_FILE, track))]
        mediapackage = http_request(service + '/addTrack', fields)

    # ingest
    logger.info('Ingest recording')
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
        logger.error('Start ingest failed')
        logger.error(traceback.format_exc())
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
    logger.info('Shutting down ingest service')
    set_service_status(Service.INGEST, ServiceStatus.STOPPED)


def run():
    '''Start the capture agent.
    '''
    configure_service('ingest')
    configure_service('capture.admin')
    control_loop()
