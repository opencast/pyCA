#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2016, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.config import config
from pyca.db import get_session, Event, Status
from base64 import b64decode
from datetime import datetime
from dateutil.tz import tzutc
import dateutil.parser
import errno
import json
import logging
import os
import os.path
import pycurl
import sys
from random import randrange
import time
import traceback
if sys.version_info[0] == 2:
    from cStringIO import StringIO as bio
else:
    from io import BytesIO as bio


# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s ' +
                    '[%(filename)s:%(lineno)s:%(funcName)s()] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def get_service(service_type):
    '''Get available service endpoints for a given service type from the
    Opencast ServiceRegistry.
    '''
    endpoint = '/services/available.json?serviceType=' + str(service_type)
    url = '%s%s' % (config()['server']['url'], endpoint)
    response = http_request(url).decode('utf-8')
    services = json.loads(response).get('services', {}).get('service', [])
    # This will give us either a list or one element. Let us make sure, it is
    # a list
    try:
        services.get('type')
        services = [services]
    except AttributeError:
        pass
    endpoints = [s['host'] + s['path'] for s in services
                 if s['online'] and s['active']]
    for endpoint in endpoints:
        logging.info('Endpoint for %s: %s', service_type, endpoint)
    return endpoints


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
    url = '%s/agents/%s' % (config()['service-capture'][0],
                            config()['agent']['name'])
    try:
        response = http_request(url, params).decode('utf-8')
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
    # If this is a backup CA we don't update the recording state. The actual
    # CA does that and we don't want to mess with it.  We will just run
    # silently
    # in the background:
    if config()['agent']['backup_mode']:
        return
    params = [('state', status)]
    url = '%s/recordings/%s' % (config()['service-capture'][0], recording_id)
    try:
        result = http_request(url, params)
        logging.info(result)
    except:
        # Ignore errors (e.g. network issues) as it's more important to get
        # the recording as to set the correct current state in the admin ui.
        logging.warning('Could not set recording state')
        logging.warning(traceback.format_exc())


def parse_ical(vcal):
    '''Parse Opencast schedule iCalendar file and return events as dict
    '''
    vcal = vcal.replace('\r\n ', '').replace('\r\n\r\n', '\r\n')
    vevents = vcal.split('\r\nBEGIN:VEVENT\r\n')
    del(vevents[0])
    events = []
    for vevent in vevents:
        event = {}
        for line in vevent.split('\r\n'):
            line = line.split(':', 1)
            key = line[0].lower()
            if len(line) <= 1 or key == 'end':
                continue
            if key.startswith('dt'):
                event[key] = unix_ts(dateutil.parser.parse(line[1]))
                continue
            if not key.startswith('attach'):
                event[key] = line[1]
                continue
            # finally handle attachments
            event['attach'] = event.get('attach', [])
            attachment = {}
            for x in [x.split('=') for x in line[0].split(';')]:
                if x[0].lower() in ['fmttype', 'x-apple-filename']:
                    attachment[x[0].lower()] = x[1]
            attachment['data'] = b64decode(line[1]).decode('utf-8')
            event['attach'].append(attachment)
        events.append(event)
    return events


def update_event_status(event, status):
    '''Update the status of a particular event in the database.
    '''
    db = get_session()
    db.query(Event).filter(Event.start == event.start)\
                   .update({'status': status})
    event.status = status
    db.commit()


def get_schedule():
    '''Try to load schedule from the Matterhorn core. Returns a valid schedule
    or None on failure.
    '''
    try:
        uri = '%s/calendars?agentid=%s' % (config()['service-scheduler'][0],
                                           config()['agent']['name'])
        lookahead = config()['agent']['cal_lookahead'] * 24 * 60 * 60
        if lookahead:
            uri += '&cutoff=%i' % ((get_timestamp() + lookahead) * 1000)
        vcal = http_request(uri)
    except:
        logging.error('Could not get schedule')
        logging.error(traceback.format_exc())
        return False

    cal = None
    try:
        cal = parse_ical(vcal.decode('utf-8'))
    except:
        logging.error('Could not parse ical')
        logging.error(traceback.format_exc())
        return False
    db = get_session()
    db.query(Event).filter(Event.status == Status.UPCOMING)\
                   .filter(Event.protected == False)\
                   .delete()  # noqa
    for event in cal:
        # Ignore events that have already ended
        if event['dtend'] <= get_timestamp():
            continue
        e = Event()
        e.start = event['dtstart']
        e.end = event['dtend']
        e.uid = event.get('uid')
        e.set_data(event)
        db.add(e)
    db.commit()
    return True


def unix_ts(dtval):
    '''Convert datetime into a unix timestamp.

    :param dt: datetime to convert
    '''
    epoch = datetime(1970, 1, 1, 0, 0, tzinfo=tzutc())
    delta = (dtval - epoch)
    return delta.days * 24 * 3600 + delta.seconds


def get_timestamp():
    '''Get current unix timestamp
    '''
    if config()['agent']['ignore_timezone']:
        return unix_ts(datetime.now())
    return unix_ts(datetime.now(tzutc()))


def get_config_params(properties):
    '''Extract the set of configuration parameters from the properties attached
    to the schedule
    '''
    param = []
    wdef = 'full'
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
    duration = event.end - get_timestamp()
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
        with open(os.path.join(event.directory(), filename), 'w') as f:
            f.write(value)

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
    update_event_status(event, Status.SUCCESS)
    register_ca(status='idle')
    return True


def http_request(url, post_data=None):
    '''Make an HTTP request to a given URL with optional parameters.
    '''
    buf = bio()
    curl = pycurl.Curl()
    curl.setopt(curl.URL, url.encode('ascii', 'ignore'))

    # Disable HTTPS verification methods if insecure is set
    if config()['server']['insecure']:
        curl.setopt(curl.SSL_VERIFYPEER, 0)
        curl.setopt(curl.SSL_VERIFYHOST, 0)

    if config()['server']['certificate']:
        # Make sure verification methods are turned on
        curl.setopt(curl.SSL_VERIFYPEER, 1)
        curl.setopt(curl.SSL_VERIFYHOST, 2)
        # Import your certificates
        curl.setopt(pycurl.CAINFO, config()['server']['certificate'])

    if post_data:
        curl.setopt(curl.HTTPPOST, post_data)
    curl.setopt(curl.WRITEFUNCTION, buf.write)
    curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
    curl.setopt(pycurl.USERPWD, "%s:%s" % (config()['server']['username'],
                                           config()['server']['password']))
    curl.setopt(curl.HTTPHEADER, ['X-Requested-Auth: Digest'])
    curl.perform()
    status = curl.getinfo(pycurl.HTTP_CODE)
    curl.close()
    if int(status / 100) != 2:
        raise Exception('ERROR: Request to %s failed (HTTP status code %i)' %
                        (url, status))
    result = buf.getvalue()
    buf.close()
    return result


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
        with open('%s/episode.xml' % recording_dir, 'r') as episodefile:
            dublincore = episodefile.read().encode('utf8', 'ignore')
        fields = [('mediaPackage', mediapackage),
                  ('flavor', 'dublincore/episode'),
                  ('dublinCore', dublincore)]
        mediapackage = http_request(service + '/addDCCatalog', fields)

    # add series DublinCore catalog
    if os.path.isfile('%s/series.xml' % recording_dir):
        logging.info('Adding series DC catalog')
        dublincore = ''
        with open('%s/series.xml' % recording_dir, 'r') as seriesfile:
            dublincore = seriesfile.read().encode('utf8', 'ignore')
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
    fields = [('mediaPackage', mediapackage),
              ('workflowDefinitionId', workflow_def),
              ('workflowInstanceId', recording_id.encode('ascii', 'ignore'))]
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


def list_failed():
    '''List all recordings that either failed to upload or finish recording.'''
    q = get_session().query(Event)\
                     .filter((Event.status == Status.FAILED_UPLOADING) |
                             (Event.status == Status.FAILED_RECORDING))
    if q.count():
        logging.info('found {0} failed recordings:'.format(q.count()))
        for event in q:
            logging.info('\t{0} at \t{1} with reason: \t{2}'.format(event.uid,
                         time.ctime(event.start), event.status))


def control_loop():
    '''Main loop of the capture agent, retrieving and checking the schedule as
    well as starting the capture process if necessry.
    '''
    last_update = 0
    register = False
    while True:
        # Get next recording
        q = get_session().query(Event)\
                         .filter(Event.start <= get_timestamp())\
                         .filter(Event.end > get_timestamp())
        if q.count():
            event = q[0]
            safe_start_capture(event)
            # If something went wrong, we do not want to restart the capture
            # continuously, thus we sleep for the rest of the recording time.
            spare_time = max(0, event.end - get_timestamp())
            if spare_time:
                logging.warning('Capture command finished but there are %i '
                                'seconds remaining. Sleeping...', spare_time)
                time.sleep(spare_time)

        last_update_delta = get_timestamp() - last_update
        if last_update_delta > config()['agent']['update_frequency']:
            # Ensure capture agent is registered before asking for a schedule
            if register:
                if register_ca():
                    register = False
                else:
                    logging.error('Could not register capture agent. '
                                  'This might be a connection issue.')
            # Try getting an updated schedult
            if not get_schedule():
                # Re-register before next try if there was a connection error
                register = True
            last_update = get_timestamp()
            q = get_session().query(Event)\
                             .filter(Event.end > get_timestamp())
            if q.count():
                logging.info('Next scheduled recording: %s',
                             datetime.fromtimestamp(q[0].start))
            else:
                logging.info('No scheduled recording')
        time.sleep(1.0)


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
    ensurelist = lambda x: x if type(x) == list else [x]
    flavors = ensurelist(config()['capture']['flavors'])
    files = ensurelist(config()['capture']['files'])
    files = [f.replace('{{dir}}', directory) for f in files]
    files = [f.replace('{{name}}', name) for f in files]
    return zip(flavors, files)


def test():
    '''Make a test run doing a 10sec recording.
    '''
    logging.info('Starting test recording (10sec)')
    name = 'test-%i' % get_timestamp()
    logging.info('Recording name: %s', name)
    directory = '%s/%s' % (config()['capture']['directory'], name)
    logging.info('Recording directory: %s', directory)
    try_mkdir(config()['capture']['directory'])
    os.mkdir(directory)
    logging.info('Created recording directory')
    logging.info('Start recording')
    tracks = recording_command(directory, name, 2)
    logging.info('Finished recording')

    logging.info('Testing Ingest')
    config()['service-ingest'] = ['']
    sys.modules[__name__].http_request = lambda x, y=False: None
    ingest(tracks, directory, '123', 'fast', '')


def try_mkdir(directory):
    '''Try to create a directory. Pass without error if it already exists.
    '''
    try:
        os.mkdir(directory)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise err


def run():
    '''Start the capture agent.
    '''
    # TODO:   url = '%s%s' % (config()['server']['url'], endpoint)
    if config()['server']['insecure']:
        logging.warning('INSECURE: HTTPS CHECKS ARE TURNED OFF. A SECURE '
                        'CONNECTION IS NOT GUARANTEED')
    if config()['server']['certificate']:
        try:
            with open(config()['server']['certificate'], 'r'):
                pass
        except IOError as err:
            logging.warning('Could not read certificate file: %s', err)

    while (not config().get('service-ingest') or
           not config().get('service-capture') or
           not config().get('service-scheduler')):
        try:
            config()['service-ingest'] = \
                get_service('org.opencastproject.ingest')
            config()['service-capture'] = \
                get_service('org.opencastproject.capture.admin')
            config()['service-scheduler'] = \
                get_service('org.opencastproject.scheduler')
        except pycurl.error:
            logging.error('Could not get service endpoints. Retrying in 5s')
            logging.error(traceback.format_exc())
            time.sleep(5.0)

    while not register_ca():
        time.sleep(5.0)

    get_schedule()
    try:
        control_loop()
    except KeyboardInterrupt:
        pass
    register_ca(status='unknown')
