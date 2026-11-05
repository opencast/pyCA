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
import importlib.metadata
import json
import logging
import os
import os.path
import platform
import pycurl
import time
from io import BytesIO as bio
from urllib.parse import quote as urlquote


logger = logging.getLogger(__name__)

# Whether the CA API version assigned by Opencast has been verified already
_version_checked = False


def http_request(url, post_data=None, timeout=None):
    '''Make an HTTP request to a given URL with optional parameters.
    '''
    logger.debug('Requesting URL: %s', url)
    buf = bio()
    curl = pycurl.Curl()
    curl.setopt(curl.URL, url.encode('ascii', 'ignore'))

    # Use cookies if configured
    if config('server', 'cookiefile'):
        curl.setopt(curl.COOKIEJAR, config('server', 'cookiefile'))
        curl.setopt(curl.COOKIEFILE, config('server', 'cookiefile'))

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

    if config('ingest', 'upload_rate') > 0:
        curl.setopt(
            curl.MAX_SEND_SPEED_LARGE,
            config('ingest', 'upload_rate'))

    curl.setopt(curl.CONNECTTIMEOUT, config('http', 'connection_timeout'))
    if timeout is not None:
        curl.setopt(curl.TIMEOUT, timeout)
    else:
        curl.setopt(curl.TIMEOUT, config('http', 'timeout'))

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
    override = config('server', 'service_overrides', service_type)
    if override:
        logger.info('Overriding endpoint for %s: %s', service_type, override)
        return [override]

    # Get available services from Opencast
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


def service(service_name, force_update=False):
    '''Get the location of a given service from Opencast and add it to the
    current configuration.

    :param service_name: Name of the service type to request locations for
    :param force_update: Force an update, possibly wait for a service to
                         become available if none is available right now.
    :return: List of service locations
    '''
    service_id = f'org.opencastproject.{service_name}'
    service_url = config('services', service_id)
    logger.debug('Cached service URLs for %s: %s', service_name, service_url)
    if service_url and not force_update:
        return service_url

    # Get service from Opencast server
    config('services')[service_id] = []
    while not config('services', service_id) and not terminate():
        try:
            config('services')[service_id] = get_service(service_id)
            logger.debug('Updates service URL for %s: %s',
                         service_name,
                         config('services', service_id))
        except pycurl.error:
            logger.exception('Could not get %s endpoint. Retry in 5s',
                             service_name)
            time.sleep(5.0)
    return config('services', service_id)


def ensurelist(x):
    '''Ensure an element is a list.'''
    return x if type(x) is list else [x]


def agent_version():
    '''Get the version of pyCA, used as firmware revision of the agent.
    '''
    try:
        return importlib.metadata.version('pyca')
    except importlib.metadata.PackageNotFoundError:
        return 'unknown'


def agent_configuration():
    '''Build the CA API 2.x agent configuration which describes the agent
    and its capabilities to Opencast.

    Optional keys (inputs, stream configurations, device positions, device
    content) are deliberately not sent: Opencast rejects empty lists and pyCA
    does not support them.

    :return: Dictionary of configuration keys and string values
    '''
    return {
        'vendor.name': config('agent', 'vendor_name'),
        'vendor.model': config('agent', 'vendor_model'),
        'vendor.hardware': config('agent', 'vendor_hardware')
        or platform.machine() or 'unknown',
        'vendor.firmware': config('agent', 'vendor_firmware')
        or agent_version(),
        # pyCA records to local storage and ingests afterwards.
        'capture.local.capable': 'true',
        'capture.local.canstartpaused': 'false',
        'capture.stream.capable': 'false',
    }


def register_ca(status='idle'):
    '''Register this capture agent at the Opencast admin server so that it
    shows up in the admin interface, then send the current agent state and the
    agent configuration (required to be recognized as a CA API 2.x agent).

    :param status: Current status of the capture agent
    '''
    # If this is a backup CA we don't tell the Opencast core that we are
    # here.  We will just run silently in the background:
    if config('agent', 'backup_mode'):
        return
    service_endpoint = service('capture.admin')
    if not service_endpoint:
        logger.warning('Missing endpoint for updating agent status.')
        return
    name = urlquote(config('agent', 'name').encode('utf-8'), safe='')

    # Agent state
    params = [('address', config('ui', 'url')), ('state', status)]
    url = f'{service_endpoint[0]}/agents/{name}'
    try:
        response = http_request(url, params).decode('utf-8')
        if response:
            logger.info(response)
    except pycurl.error as e:
        logger.warning('Could not set agent state to %s: %s', status, e)

    # Agent configuration. Opencast expects a JSON object of string values.
    params = [('configuration', json.dumps(agent_configuration()))]
    url = f'{service_endpoint[0]}/agents/{name}/configuration'
    try:
        response = http_request(url, params).decode('utf-8')
        # The response repeats the whole configuration. Do not log this with
        # every update at info level.
        if response:
            logger.debug(response)
    except pycurl.error as e:
        logger.warning('Could not set agent configuration: %s', e)
        return

    if not _version_checked:
        check_agent_version(service_endpoint[0], name)


def check_agent_version(endpoint, name):
    '''Verify that Opencast registered this agent as a CA API 2.x agent and
    log a warning if it did not (e.g. because Opencast does not support CA
    API 2.x yet). Opencast reports the version it assigned in the agent
    configuration under the key `opencast.agent.version`.

    The check is done only once per process, as soon as Opencast has given a
    usable answer, to avoid repeating the warning with every update.

    :param endpoint: Location of the capture admin service
    :param name: URL quoted name of this agent
    '''
    global _version_checked
    url = f'{endpoint}/agents/{name}/configuration.json'
    try:
        response = json.loads(http_request(url).decode('utf-8'))
        items = response['properties-response']['properties']['item']
        version = {item['key']: item['value']
                   for item in ensurelist(items)}.get('opencast.agent.version')
    except (pycurl.error, ValueError, KeyError, TypeError) as e:
        # No usable answer. Try again with the next update.
        logger.debug('Could not verify agent version: %s', e)
        return
    _version_checked = True
    if str(version) == '2':
        logger.info('Opencast registered this agent as CA API 2.x agent')
    else:
        logger.warning('Opencast did not register this agent as CA API 2.x '
                       'agent (reported version: %s). Does your Opencast '
                       'support CA API 2.x?', version)


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
    url = service('capture.admin')[0]
    url += f'/recordings/{recording_id}'
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
