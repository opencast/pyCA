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

def get_input_params(event):
    '''Extract the input configuration parameters from the properties attached
    to the schedule-entry
    '''

    inputs = []    
    for attachment in event.get_data().get('attach'):
        data = attachment.get('data')
        if (attachment.get('x-apple-filename') == 'org.opencastproject.capture.agent.properties'):    
            for prop in data.split('\n'):
                if prop.startswith('capture.device.names'):
                    param = prop.split('=', 1)
                    inputs = param[1].split(',')
                    break               
    return inputs


def trackinput_selected(event,flavor, track):
    ''' check if input corresponding to flavor is selected in schedule-attachment
    parameter 'capture.device.names'
    returns True if input is selected or if capture.device.names='' 
    ''' 

    # inputs from pyca.conf
    inputs_conf = config('agent', 'inputs')
    
    # if no inputs defined, return True -> add all tracks to mediapackage
    if (inputs_conf == ['']):
        logger.info('No inputs in config defined')
        return True
                
    # flavors from pyca.conf
    flavors_conf = config('capture', 'flavors')  
    
    # inputs in event attachment
    inputs_event = get_input_params(event)
	
	# if no inputs in attachment, return True -> add all tracks to mediapackage
    if (inputs_event == ['']):
        logger.info('No inputs in schedule')
	    # print('No inputs in event attachment')
        return True
    
    # Input corresponding to track-flavor from pyca.conf
    input_track = inputs_conf[flavors_conf.index(flavor)]
        
    if input_track in inputs_event:
        # Input corresponding to flavor is selected in attachment
        return True
    
    # Input corresponding to flavor is not selected in attachment
    return False


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
    # nosec: we do not need a secure random number here
    service_url = service_url[random.randrange(0, len(service_url))]  # nosec
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
        if (trackinput_selected(event, flavor, track) == True):
            logger.info('Adding track (%s -> %s)', flavor, track)
            track = track.encode('ascii', 'ignore')
            fields = [('mediaPackage', mediapackage), ('flavor', flavor),
                  ('BODY1', (pycurl.FORM_FILE, track))]
            mediapackage = http_request(service_url + '/addTrack', fields)
        else:
            logger.info('Ignoring track (%s -> %s)', flavor, track)

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
            # nosec: we do not need a secure random number here
            delay = random.randint(config('ingest', 'delay_min'),  # nosec
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
