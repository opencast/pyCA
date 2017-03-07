from pyca.config import config
from pyca.db import get_session, Status, UpcomingEvent, RecordedEvent
from pyca.db import Service, ServiceStatus
from pyca.utils import get_service_status
from datetime import datetime
import logging
from flask import request, jsonify
from pyca.ui import app



def json_error(code=500, title='Internal Error'):
    error = {
        'errors': [
            {
                'status': code,
                'title': title
            }
        ]
    }
    
    return jsonify(error)

@app.route("/api/internal_state.json")
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


@app.route("/api/event.json", methods=['GET'])
def event():
    '''Serve a json representation of events
    '''
    
    try:
        db = get_session()
        upcoming_events = db.query(UpcomingEvent)\
                            .order_by(UpcomingEvent.start)
        recorded_events = db.query(RecordedEvent)\
                            .order_by(RecordedEvent.start.desc())
    except:
        return json_error(), 500
    
    answer = { 'data': [] }
    for events in [upcoming_events, recorded_events]:
        for e in events:
            i = {
                'type': 'event',
                'id': e.uid,
                'attributes': {
                    'start': datetime.fromtimestamp(e.start).isoformat(),
                    'end': datetime.fromtimestamp(e.end).isoformat(),
                    'status': Status.str(Status.UPCOMING)
                }
            }

            if hasattr(e, 'status'):
                i['attributes']['status'] = Status.str(e.status)

            answer['data'].append(i)

    return jsonify(answer)


@app.route("/api/event.json", methods=['DELETE'])
def delete_event():
    '''Delete a specific event identified by ?id parameter
    '''
    uid = request.args.get('id', 0)
    if uid == 0:
        return json_error(400, 'missing id parameter'), 400
    
    try:
        db = get_session()
        event = db.query(RecordedEvent).filter(RecordedEvent.uid == uid)
        if event.count():
            logging.info('deleting event %s via api', uid)
            # TODO
        else:
            return json_error(404, 'no event with id'), 404
    except:
        return json_error(), 500
    return uid

@app.route("/api/event.json", methods=['POST'])
def reingest_event():
    '''Reingest a specific event identified by ?id parameter
    '''
    pass