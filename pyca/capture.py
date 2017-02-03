#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import http_request, timestamp, try_mkdir, configure_service
from pyca.utils import ensurelist
from pyca.config import config
from pyca.db import get_session, RecordedEvent, UpcommingEvent, Status
import logging
import os
import os.path
import pycurl
from random import randrange
import time
import traceback


def register_ca(status='idle'):
    '''Register this capture agent at the Matterhorn admin server so that it
    shows up in the admin interface.

    :param address: Address of the capture agent web ui
    :param status: Current status of the capture agent
    '''
    # If this is a backup CA we don't tell the Matterhorn core that we are
    # here.  We will just run silently in the background:
    if config()['agent']['backup_mode']:
        return True
    params = [('address', config()['ui']['url']), ('state', status)]
    url = '%s/agents/%s' % (config()['service-capture.admin'][0],
                            config()['agent']['name'])
    try:
        response = http_request(url, params).decode('utf-8')
        if response:
            logging.info(response)
    except:
        # Ignore errors (e.g. network issues) as it's more important to get
        # the recording as to set the correct current state in the admin ui.
        logging.warning('Could not set capture agent state')
        logging.warning(traceback.format_exc())
        return False
    return True


def recording_state(recording_id, status):
    '''Send the state of the current recording to the Matterhorn core.

    :param recording_id: ID of the current recording
    :param status: Status of the recording
    '''
    # If this is a backup CA we do not update the recording state since the
    # actual CA does that and we want to interfere.  We will just run silently
    # in the background:
    if config()['agent']['backup_mode']:
        return
    params = [('state', status)]
    url = config()['service-capture.admin'][0]
    url += '/recordings/%s' % recording_id
    try:
        result = http_request(url, params)
        logging.info(result)
    except:
        # Ignore errors (e.g. network issues) as it's more important to get
        # the recording as to set the correct current state in the admin ui.
        logging.warning('Could not set recording state')
        logging.warning(traceback.format_exc())


def update_event_status(event, status):
    '''Update the status of a particular event in the database.
    '''
    db = get_session()
    db.query(RecordedEvent).filter(RecordedEvent.start == event.start)\
                           .update({'status': status})
    event.status = status
    db.commit()


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


def start_capture(event):
    '''Start the capture process, creating all necessary files and directories
    as well as ingesting the captured files if no backup mode is configured.
    '''
    logging.info('Start recording')

    # First move event to recording_event table
    db = get_session()
    event = RecordedEvent(event)
    db.add(event)
    db.commit()

    duration = event.end - timestamp()
    try_mkdir(config()['capture']['directory'])
    os.mkdir(event.directory())

    # Set state
    register_ca(status='capturing')
    recording_state(event.uid, 'capturing')
    update_event_status(event, Status.RECORDING)

    tracks = []
    try:
        tracks = recording_command(event.directory(), event.name(), duration)
    except:
        logging.error('Recording command failed')
        logging.error(traceback.format_exc())
        # Update state
        recording_state(event.uid, 'capture_error')
        update_event_status(event, Status.FAILED_RECORDING)
        register_ca(status='idle')
        return False

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
    register_ca(status='uploading')
    recording_state(event.uid, 'uploading')
    update_event_status(event, Status.UPLOADING)

    try:
        ingest(tracks, event.directory(), event.uid, workflow_def,
               workflow_config)
    except:
        logging.error('Something went wrong during the upload')
        logging.error(traceback.format_exc())
        # Update state if something went wrong
        recording_state(event.uid, 'upload_error')
        update_event_status(event, Status.FAILED_UPLOADING)
        register_ca(status='idle')
        return False

    # Update state
    recording_state(event.uid, 'upload_finished')
    update_event_status(event, Status.FINISHED_UPLOADING)
    register_ca(status='idle')
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


def safe_start_capture(event):
    '''Start a capture process but make sure to catch any errors during this
    process, log them but otherwise ignore them.
    '''
    try:
        return start_capture(event)
    except:
        logging.error('Start capture failed')
        logging.error(traceback.format_exc())
        register_ca(status='idle')
        return False


def recording_command(directory, name, duration):
    '''Run the actual command to record the a/v material.
    '''
    preview_dir = config()['capture']['preview_dir']
    cmd = config()['capture']['command']
    cmd = cmd.replace('{{time}}', str(duration))
    cmd = cmd.replace('{{dir}}', directory)
    cmd = cmd.replace('{{name}}', name)
    cmd = cmd.replace('{{previewdir}}', preview_dir)
    logging.info(cmd)
    if os.system(cmd):
        raise Exception('Recording failed')

    # Remove preview files:
    for preview in config()['capture']['preview']:
        try:
            os.remove(preview.replace('{{previewdir}}', preview_dir))
        except OSError:
            logging.warning('Could not remove preview files')
            logging.warning(traceback.format_exc())

    # Return [(flavor,path),…]
    flavors = ensurelist(config()['capture']['flavors'])
    files = ensurelist(config()['capture']['files'])
    files = [f.replace('{{dir}}', directory) for f in files]
    files = [f.replace('{{name}}', name) for f in files]
    return zip(flavors, files)


def control_loop():
    '''Main loop of the capture agent, retrieving and checking the schedule as
    well as starting the capture process if necessry.
    '''
    while True:
        # Get next recording
        register_ca()
        events = get_session().query(UpcommingEvent)\
                              .filter(UpcommingEvent.start <= timestamp())\
                              .filter(UpcommingEvent.end > timestamp())
        if events.count():
            safe_start_capture(events[0])
        time.sleep(1.0)


def run():
    '''Start the capture agent.
    '''
    configure_service('ingest')
    configure_service('capture.admin')

    while not register_ca():
        time.sleep(5.0)

    try:
        control_loop()
    except KeyboardInterrupt:
        pass
    register_ca(status='unknown')
