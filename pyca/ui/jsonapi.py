from pyca.config import config
from pyca.db import get_session, Status, UpcomingEvent, RecordedEvent
from pyca.db import Service, ServiceStatus
from pyca.utils import get_service_status
from datetime import datetime
import logging
from flask import request, jsonify
from pyca.ui import app


@app.route('/api/services')
def internal_state():
    '''Serve a json representation of internal agent state
    '''
    state = {
        'capture' : ServiceStatus.str(get_service_status(Service.CAPTURE)),
        'ingest' : ServiceStatus.str(get_service_status(Service.INGEST)),
        'schedule' : ServiceStatus.str(get_service_status(Service.SCHEDULE)),
        'agentstate' : ServiceStatus.str(get_service_status(Service.AGENTSTATE))
    }
    return jsonify(state)


@app.route('/api/events')
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
def event(uid):
    '''Return a specific event es JSON
    '''
    db = get_session()
    event = db.query(RecordedEvent).filter(RecordedEvent.uid == uid).first() \
            or db.query(UpcomingEvent).filter(UpcomingEvent.uid == uid).first()

    if event:
        return jsonify(event.serialize())
    return '', 404


@app.route('/api/events/<uid>', methods=['DELETE'])
def delete_event(uid):
    '''Delete a specific event identified by its uid

    Returns 204 if the action was successful.
    '''
    db = get_session()
    db.query(RecordedEvent).filter(RecordedEvent.uid == uid).delete()
    logging.info('deleting event %s via api', uid)
    db.commit()
    return '', 204


@app.route('/api/events/<uid>', methods=['PATCH'])
def reingest_event(uid):
    '''Reingest a specific event identified by ?id parameter
    '''
    db = get_session()
    db.query(RecordedEvent).filter(RecordedEvent.uid == uid).delete()
    logging.info('deleting event %s via api', uid)
    db.commit()
    return '', 204
