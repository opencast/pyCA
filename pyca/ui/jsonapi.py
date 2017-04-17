# -*- coding: utf-8 -*-
from flask import jsonify, make_response, request
from pyca.db import Service, ServiceStatus, UpcomingEvent, RecordedEvent
from pyca.db import get_session, Status
from pyca.ui import app
from pyca.ui.utils import requires_auth
from pyca.utils import get_service_status
import logging

logger = logging.getLogger(__name__)


@app.route('/api/services')
@requires_auth
def internal_state():
    '''Serve a json representation of internal agent state
    '''
    state = {
        'capture': ServiceStatus.str(get_service_status(Service.CAPTURE)),
        'ingest': ServiceStatus.str(get_service_status(Service.INGEST)),
        'schedule': ServiceStatus.str(get_service_status(Service.SCHEDULE)),
        'agentstate': ServiceStatus.str(get_service_status(Service.AGENTSTATE))
    }
    return jsonify(state)


@app.route('/api/events/')
@requires_auth
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
    return jsonify(result)


@app.route('/api/events/<uid>')
@requires_auth
def event(uid):
    '''Return a specific event es JSON
    '''
    db = get_session()
    event = db.query(RecordedEvent).filter(RecordedEvent.uid == uid).first() \
        or db.query(UpcomingEvent).filter(UpcomingEvent.uid == uid).first()

    if event:
        return jsonify(event.serialize())
    return make_response(jsonify('No event with specified uid'), 404)


@app.route('/api/events/<uid>', methods=['DELETE'])
@requires_auth
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
        return make_response(jsonify('No event with specified uid'), 404)
    events.delete()
    logger.info('deleting event %s via api', uid)
    db.commit()
    return make_response('', 204)


@app.route('/api/events/<uid>', methods=['PATCH'])
@requires_auth
def modify_event(uid):
    '''Modify an event specified by its uid. The modifications for the event
    are expected as JSON with the content type correctly set in the request.
    '''
    try:
        data = request.get_json()
        # Check attributes
        for key in data.keys():
            if key not in ('status', 'start', 'end'):
                return make_response(jsonify('Invalid data'), 400)
        # Check new status
        new_status = data.get('status')
        if new_status:
            data['status'] = int(getattr(Status, new_status.upper()))
    except Exception:
        return make_response(jsonify('Invalid data'), 400)

    db = get_session()
    event = db.query(RecordedEvent).filter(RecordedEvent.uid == uid).first()
    if not event:
        return make_response(jsonify('No event with specified uid'), 404)
    event.start = data.get('start', event.start)
    event.end = data.get('end', event.end)
    event.status = data.get('status', event.status)
    logger.debug('Updating event %s via api', uid)
    db.commit()
    return jsonify(event.serialize())
