# -*- coding: utf-8 -*-
from flask import jsonify, make_response, request
from pyca.config import config
from pyca.db import Service, ServiceStatus, UpcomingEvent, \
    RecordedEvent, UpstreamState
from pyca.db import with_session, Status, ServiceStates
from pyca.ui import app
from pyca.ui.utils import requires_auth, jsonapi_mediatype
from pyca.utils import get_service_status, ensurelist, timestamp
import logging
import os
import psutil
import shutil
import subprocess

logger = logging.getLogger(__name__)


def make_error_response(error, status=500):
    ''' Return a response with a jsonapi error object
    '''
    content = {
        'errors': [{
            'status': status,
            'title': error
        }]
    }
    return make_response(jsonify(content), status)


def make_data_response(data, status=200):
    ''' Return a response with a list of jsonapi data objects
    '''
    content = {'data': ensurelist(data)}
    return make_response(jsonify(content), status)


@app.route('/api/name')
@requires_auth
@jsonapi_mediatype
def get_name():
    '''Serve the name of the capure agent via json.
    '''
    return make_response(
        jsonify({'meta': {'name': config('agent', 'name')}}))


@app.route('/api/previews')
@requires_auth
@jsonapi_mediatype
def get_images():
    '''Serve the list of preview images via json.
    '''
    # Get IDs of existing preview images
    preview = config('capture', 'preview')
    previewdir = config('capture', 'preview_dir')
    preview = [p.replace('{{previewdir}}', previewdir) for p in preview]
    preview = zip(preview, range(len(preview)))

    # Create return
    preview = [{'attributes': {'id': p[1]}, 'id': str(p[1]), 'type': 'preview'}
               for p in preview if os.path.isfile(p[0])]
    return make_data_response(preview)


@app.route('/api/services')
@requires_auth
@jsonapi_mediatype
def internal_state():
    '''Serve a json representation of internal agentstate as meta data
    '''
    data = {'services': {
        'capture': ServiceStatus.str(get_service_status(Service.CAPTURE)),
        'ingest': ServiceStatus.str(get_service_status(Service.INGEST)),
        'schedule': ServiceStatus.str(get_service_status(Service.SCHEDULE)),
        'agentstate': ServiceStatus.str(get_service_status(Service.AGENTSTATE))
    }}
    return make_response(jsonify({'meta': data}))


@app.route('/api/events/')
@requires_auth
@jsonapi_mediatype
@with_session
def events(db):
    '''Serve a JSON representation of events splitted by upcoming and already
    recorded events.
    '''
    upcoming_events = db.query(UpcomingEvent)\
                        .order_by(UpcomingEvent.start)
    recorded_events = db.query(RecordedEvent)\
                        .order_by(RecordedEvent.start.desc())

    result = [event.serialize() for event in upcoming_events]
    result += [event.serialize() for event in recorded_events]
    return make_data_response(result)


@app.route('/api/events/<uid>')
@requires_auth
@jsonapi_mediatype
@with_session
def event(db, uid):
    '''Return a specific events JSON
    '''
    event = db.query(RecordedEvent).filter(RecordedEvent.uid == uid).first() \
        or db.query(UpcomingEvent).filter(UpcomingEvent.uid == uid).first()

    if event:
        return make_data_response(event.serialize())
    return make_error_response('No event with specified uid', 404)


@app.route('/api/events/<uid>', methods=['DELETE'])
@requires_auth
@jsonapi_mediatype
@with_session
def delete_event(db, uid):
    '''Delete a specific event identified by its uid. Note that only recorded
    events can be deleted. Events in the buffer for upcoming events are
    regularly replaced anyway and a manual removal could have unpredictable
    effects.

    Use ?hard=true parameter to delete the recorded files on disk as well.

    Returns 204 if the action was successful.
    Returns 404 if event does not exist
    '''
    logger.info('deleting event %s via api', uid)
    events = db.query(RecordedEvent).filter(RecordedEvent.uid == uid)
    if not events.count():
        return make_error_response('No event with specified uid', 404)
    hard_delete = request.args.get('hard', 'false')
    if hard_delete == 'true':
        logger.info('deleting recorded files at %s', events[0].directory())
        shutil.rmtree(events[0].directory())
    events.delete()
    db.commit()
    return make_response('', 204)


@app.route('/api/events/<uid>', methods=['PATCH'])
@requires_auth
@jsonapi_mediatype
@with_session
def modify_event(db, uid):
    '''Modify an event specified by its uid. The modifications for the event
    are expected as JSON with the content type correctly set in the request.

    Note that this method works for recorded events only. Upcoming events part
    of the scheduler cache cannot be modified.
    '''
    try:
        data = request.get_json()['data'][0]
        if data['type'] != 'event' or data['id'] != uid:
            return make_error_response('Invalid data', 400)
        # Check attributes
        for key in data['attributes'].keys():
            if key not in ('status', 'start', 'end'):
                return make_error_response('Invalid data', 400)
        # Check new status
        new_status = data['attributes'].get('status')
        if new_status:
            new_status = new_status.upper().replace(' ', '_')
            data['attributes']['status'] = int(getattr(Status, new_status))
    except Exception:
        return make_error_response('Invalid data', 400)

    event = db.query(RecordedEvent).filter(RecordedEvent.uid == uid).first()
    if not event:
        return make_error_response('No event with specified uid', 404)
    event.start = data['attributes'].get('start', event.start)
    event.end = data['attributes'].get('end', event.end)
    event.status = data['attributes'].get('status', event.status)
    logger.debug('Updating event %s via api', uid)
    db.commit()
    return make_data_response(event.serialize())


@app.route('/api/metrics', methods=['GET'])
@requires_auth
@jsonapi_mediatype
@with_session
def metrics(dbs):
    '''Serve several metrics about the pyCA services and the machine via
    json.'''
    # Get Disk Usage
    # If the capture directory do not exists, use the parent directory.
    directory = config('capture', 'directory')
    if not os.path.exists(directory):
        directory = os.path.abspath(os.path.join(directory, os.pardir))
    total, used, free = shutil.disk_usage(directory)

    # Get Loads
    load_1m, load_5m, load_15m = os.getloadavg()

    # Get Memory
    memory = psutil.virtual_memory()

    # Get Services
    srvs = dbs.query(ServiceStates)
    services = []
    for srv in srvs:
        services.append({
            'name': Service.str(srv.type),
            'status': ServiceStatus.str(srv.status)
        })
    # Get Upstream State
    state = dbs.query(UpstreamState).filter(
        UpstreamState.url == config('server', 'url')).first()
    last_synchronized = state.last_synced.isoformat() if state else None
    return make_response(jsonify(
        {'meta': {
            'services': services,
            'disk_usage_in_bytes': {
                'total': total,
                'used': used,
                'free': free,
            },
            'memory_usage_in_bytes': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'free': memory.free,
                'cached': memory.cached,
                'buffers': memory.buffers,
            },
            'load': {
                '1m': load_1m,
                '5m': load_5m,
                '15m': load_15m,
            },
            'upstream': {
                'last_synchronized': last_synchronized,
            }
        }}))


@app.route('/api/logs')
@requires_auth
@jsonapi_mediatype
def logs():
    '''Serve a JSON representation of logs.
    '''
    cmd = config('ui', 'log_command')
    if not cmd:
        return make_error_response('Logs are disabled.', 404)

    logs = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)\
        .stdout\
        .decode('utf-8')\
        .rstrip()\
        .split('\n')
    return make_data_response({
        'id': str(timestamp()),
        'type': 'logs',
        'attributes': {
            'lines': logs}})
