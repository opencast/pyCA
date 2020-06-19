# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.config import config
from pyca import db
from datetime import datetime
from dateutil.tz import tzutc
import errno
import json
import logging
import os
import os.path
import pycurl
import time
from io import BytesIO as bio
from urllib.parse import quote as urlquote


logger = logging.getLogger(__name__)


def http_request(url, post_data=None):
    '''Make an HTTP request to a given URL with optional parameters.
    '''
    logger.debug('Requesting URL: %s', url)
    buf = bio()
    curl = pycurl.Curl()
    curl.setopt(curl.URL, url.encode('ascii', 'ignore'))

    # More verbose curl calls in debug mode
    if logger.getEffectiveLevel() == logging.DEBUG:
        curl.setopt(pycurl.VERBOSE, True)

    # Disable HTTPS verification methods if insecure is set
    if config('server', 'insecure'):
        curl.setopt(curl.SSL_VERIFYPEER, 0)
        curl.setopt(curl.SSL_VERIFYHOST, 0)

    if config('server', 'certificate'):
        # Make sure verification methods are turned on
        curl.setopt(curl.SSL_VERIFYPEER, 1)
        curl.setopt(curl.SSL_VERIFYHOST, 2)
        # Import your certificates
        curl.setopt(pycurl.CAINFO, config('server', 'certificate'))

    if post_data:
        curl.setopt(curl.HTTPPOST, post_data)
    curl.setopt(curl.WRITEFUNCTION, buf.write)
    logger.debug('Using authentication method %s',
                 config('server')['auth_method'])
    if config('server')['auth_method'] == 'digest':
        curl.setopt(curl.HTTPHEADER, ['X-Requested-Auth: Digest'])
        curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
    curl.setopt(pycurl.USERPWD, ':'.join([config('server', 'username'),
                                          config('server', 'password')]))
    curl.setopt(curl.FAILONERROR, True)
    curl.setopt(curl.FOLLOWLOCATION, True)
    curl.perform()
    curl.close()
    result = buf.getvalue()
    buf.close()
    return result


def get_service(service_type):
    '''Get available service endpoints for a given service type from the
    Opencast ServiceRegistry.
    '''
    endpoint = '/services/available.json?serviceType=' + str(service_type)
    url = config('server', 'url') + endpoint
    response = http_request(url).decode('utf-8')
    services = json.loads(response).get('services', {}).get('service', [])
    services = ensurelist(services)
    endpoints = [service['host'] + service['path'] for service in services
                 if service['online'] and service['active']]
    for endpoint in endpoints:
        logger.info(u'Endpoint for %s: %s', service_type, endpoint)
    return endpoints


def timestamp():
    '''Get current unix timestamp
    '''
    return int(datetime.now(tzutc()).timestamp())


def try_mkdir(directory):
    '''Try to create a directory. Pass without error if it already exists.
    '''
    try:
        os.mkdir(directory)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise err


def configure_service(service):
    '''Get the location of a given service from Opencast and add it to the
    current configuration.
    '''
    while not config('service-' + service) and not terminate():
        try:
            config()['service-' + service] = \
                get_service('org.opencastproject.' + service)
        except pycurl.error as e:
            logger.error('Could not get %s endpoint: %s. Retrying in 5s',
                         service, e)
            time.sleep(5.0)


def ensurelist(x):
    '''Ensure an element is a list.'''
    return x if type(x) == list else [x]


def register_ca(status='idle'):
    '''Register this capture agent at the Matterhorn admin server so that it
    shows up in the admin interface.

    :param address: Address of the capture agent web ui
    :param status: Current status of the capture agent
    '''
    # If this is a backup CA we don't tell the Matterhorn core that we are
    # here.  We will just run silently in the background:
    if config('agent', 'backup_mode'):
        return
    service_endpoint = config('service-capture.admin')
    if not service_endpoint:
        logger.warning('Missing endpoint for updating agent status.')
        return
    params = [('address', config('ui', 'url')), ('state', status)]
    name = urlquote(config('agent', 'name').encode('utf-8'), safe='')
    url = f'{service_endpoint[0]}/agents/{name}'
    try:
        response = http_request(url, params).decode('utf-8')
        if response:
            logger.info(response)
    except pycurl.error as e:
        logger.warning('Could not set agent state to %s: %s', status, e)


def recording_state(recording_id, status):
    '''Send the state of the current recording to the Matterhorn core.

    :param recording_id: ID of the current recording
    :param status: Status of the recording
    '''
    # If this is a backup CA we do not update the recording state since the
    # actual CA does that and we want to interfere.  We will just run silently
    # in the background:
    if config('agent', 'backup_mode'):
        return
    params = [('state', status)]
    url = config('service-capture.admin')[0]
    url += '/recordings/%s' % recording_id
    try:
        result = http_request(url, params).decode('utf-8')
        logger.info(result)
    except pycurl.error as e:
        logger.warning('Could not set recording state to %s: %s', status, e)


@db.with_session
def update_event_status(dbs, event, status):
    '''Update the status of a particular event in the database.
    '''
    dbs.query(db.RecordedEvent).filter(db.RecordedEvent.start == event.start)\
                               .update({'status': status})
    event.status = status
    dbs.commit()


@db.with_session
def set_service_status(dbs, service, status):
    '''Update the status of a particular service in the database.
    '''
    srv = db.ServiceStates()
    srv.type = service
    srv.status = status

    dbs.merge(srv)
    dbs.commit()


def set_service_status_immediate(service, status):
    '''Update the status of a particular service in the database and send an
    immediate signal to Opencast.
    '''
    set_service_status(service, status)
    update_agent_state()


@db.with_session
def get_service_status(dbs, service):
    '''Update the status of a particular service in the database.
    '''
    srvs = dbs.query(db.ServiceStates).filter(db.ServiceStates.type == service)

    if srvs.count():
        return srvs[0].status

    return db.ServiceStatus.STOPPED


def update_agent_state():
    '''Update the current agent state in opencast.
    '''
    configure_service('capture.admin')
    status = 'idle'

    # Determine reported agent state with priority list
    if get_service_status(db.Service.SCHEDULE) == db.ServiceStatus.STOPPED:
        status = 'offline'
    elif get_service_status(db.Service.CAPTURE) == db.ServiceStatus.BUSY:
        status = 'capturing'
    elif get_service_status(db.Service.INGEST) == db.ServiceStatus.BUSY:
        status = 'uploading'

    register_ca(status=status)


def terminate(shutdown=None):
    '''Mark process as to be terminated.
    '''
    global _terminate
    if shutdown is not None:
        _terminate = shutdown
    return '_terminate' in globals() and _terminate
