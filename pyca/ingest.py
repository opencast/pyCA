# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.config import config
from pyca.db import get_session, RecordedEvent, Status, Service, ServiceStatus
from pyca.utils import http_request, service, set_service_status
from pyca.utils import set_service_status_immediate, recording_state
from pyca.utils import update_event_status, terminate
import logging
import pycurl
import random
import sdnotify
import shutil
import time

logger = logging.getLogger(__name__)
notify = sdnotify.SystemdNotifier()


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


def ingest(event):
    '''Ingest a finished recording to the Opencast server.
    '''
    # Update status
    set_service_status(Service.INGEST, ServiceStatus.BUSY)
    notify.notify('STATUS=Uploading')
    recording_state(event.uid, 'uploading')
    update_event_status(event, Status.UPLOADING)

    # Select ingest service
    # The ingest service to use is selected at random from the available
    # ingest services to ensure that not every capture agent uses the same
    # service at the same time
    service_url = service('ingest', force_update=True)
    service_url = service_url[random.randrange(0, len(service_url))]
    logger.info('Selecting ingest service to use: ' + service_url)

    # create mediapackage
    logger.info('Creating new mediapackage')
    mediapackage = http_request(service_url + '/createMediaPackage')

    # extract workflow_def, workflow_config and add DC catalogs
    prop = 'org.opencastproject.capture.agent.properties'
    dcns = 'http://www.opencastproject.org/xsd/1.0/dublincore/'
    for attachment in event.get_data().get('attach'):
        data = attachment.get('data')
        if attachment.get('x-apple-filename') == prop:
            workflow_def, workflow_config = get_config_params(data)

        # dublin core catalogs
        elif attachment.get('fmttype') == 'application/xml' \
                and dcns in data \
                and config('ingest', 'upload_catalogs'):
            name = attachment.get('x-apple-filename', '').rsplit('.', 1)[0]
            logger.info('Adding %s DC catalog', name)
            fields = [('mediaPackage', mediapackage),
                      ('flavor', 'dublincore/%s' % name),
                      ('dublinCore', data.encode('utf-8'))]
            mediapackage = http_request(service_url + '/addDCCatalog', fields)

        else:
            logger.info('Not uploading %s', attachment.get('x-apple-filename'))
            continue

    # add track
    for (flavor, track) in event.get_tracks():
        logger.info('Adding track (%s -> %s)', flavor, track)
        track = track.encode('ascii', 'ignore')
        fields = [('mediaPackage', mediapackage), ('flavor', flavor),
                  ('BODY1', (pycurl.FORM_FILE, track))]
        mediapackage = http_request(service_url + '/addTrack', fields)

    # ingest
    logger.info('Ingest recording')
    fields = [('mediaPackage', mediapackage)]
    if workflow_def:
        fields.append(('workflowDefinitionId', workflow_def))
    if event.uid:
        fields.append(('workflowInstanceId',
                       event.uid.encode('ascii', 'ignore')))
    fields += workflow_config
    mediapackage = http_request(service_url + '/ingest', fields)

    # Update status
    recording_state(event.uid, 'upload_finished')
    update_event_status(event, Status.FINISHED_UPLOADING)
    if config('ingest', 'delete_after_upload'):
        directory = event.directory()
        logger.info("Removing uploaded event directory %s", directory)
        shutil.rmtree(directory)
    notify.notify('STATUS=Running')
    set_service_status_immediate(Service.INGEST, ServiceStatus.IDLE)

    logger.info('Finished ingest')


def safe_start_ingest(event):
    '''Start a capture process but make sure to catch any errors during this
    process, log them but otherwise ignore them.
    '''
    try:
        ingest(event)
    except Exception:
        logger.exception('Something went wrong during the upload')
        # Update state if something went wrong
        recording_state(event.uid, 'upload_error')
        update_event_status(event, Status.FAILED_UPLOADING)
        set_service_status_immediate(Service.INGEST, ServiceStatus.IDLE)


def control_loop():
    '''Main loop of the capture agent, retrieving and checking the schedule as
    well as starting the capture process if necessry.
    '''
    set_service_status_immediate(Service.INGEST, ServiceStatus.IDLE)
    notify.notify('READY=1')
    notify.notify('STATUS=Running')
    while not terminate():
        notify.notify('WATCHDOG=1')
        # Get next recording
        session = get_session()
        event = session.query(RecordedEvent)\
                       .filter(RecordedEvent.status ==
                               Status.FINISHED_RECORDING).first()
        if event:
            delay = random.randint(config('ingest', 'delay_min'),
                                   config('ingest', 'delay_max'))
            logger.info("Delaying ingest for %s seconds", delay)
            time.sleep(delay)
            safe_start_ingest(event)
        session.close()
        time.sleep(1.0)
    logger.info('Shutting down ingest service')
    set_service_status(Service.INGEST, ServiceStatus.STOPPED)


def run():
    '''Start the capture agent.
    '''

    control_loop()
