# -*- coding: utf-8 -*-
from flask import jsonify, make_response, request
from pyca.db import Service, ServiceStatus, UpcomingEvent, RecordedEvent
from pyca.db import get_session, Status
from pyca.ui import app
from pyca.ui.utils import requires_auth, jsonapi_mediatype
from pyca.utils import get_service_status, ensurelist
import logging

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
        }
    }
    return make_response(jsonify({'meta': data}))


@app.route('/api/events/')
@requires_auth
@jsonapi_mediatype
def events():
    '''Serve a JSON representation of events
    '''
    db = get_session()
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
def event(uid):
    '''Return a specific events JSON
    '''
    db = get_session()
    event = db.query(RecordedEvent).filter(RecordedEvent.uid == uid).first() \
        or db.query(UpcomingEvent).filter(UpcomingEvent.uid == uid).first()

    if event:
        return make_data_response(event.serialize())
    return make_error_response('No event with specified uid', 404)


@app.route('/api/events/<uid>', methods=['DELETE'])
@requires_auth
@jsonapi_mediatype
def delete_event(uid):
    '''Delete a specific event identified by its uid. Note that only recorded
    events can be deleted. Events in the buffer for upcoming events are
    regularly replaced anyway and a manual removal could have unpredictable
    effects.

    Returns 204 if the action was successful.
    Returns 404 if event does not exist
    '''
    db = get_session()
    events = db.query(RecordedEvent).filter(RecordedEvent.uid == uid)
    if not events.count():
        return make_error_response('No event with specified uid', 404)
    events.delete()
    logger.info('deleting event %s via api', uid)
    db.commit()
    return make_response('', 204)


@app.route('/api/events/<uid>', methods=['PATCH'])
@requires_auth
@jsonapi_mediatype
def modify_event(uid):
    '''Modify an event specified by its uid. The modifications for the event
    are expected as JSON with the content type correctly set in the request.
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
            data['status'] = int(getattr(Status, new_status.upper()))
    except Exception:
        return make_error_response('Invalid data', 400)

    db = get_session()
    event = db.query(RecordedEvent).filter(RecordedEvent.uid == uid).first()
    if not event:
        return make_error_response('No event with specified uid', 404)
    event.start = data['attributes'].get('start', event.start)
    event.end = data['attributes'].get('end', event.end)
    event.status = data['attributes'].get('status', event.status)
    logger.debug('Updating event %s via api', uid)
    db.commit()
    return make_data_response(event.serialize())
