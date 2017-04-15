# -*- coding: utf-8 -*-
'''
Simple UI telling about the current state of the capture agent.
'''
from flask import Flask, request, send_from_directory,  render_template
from pyca.config import config
from pyca.db import Service, ServiceStatus, UpcomingEvent, RecordedEvent
from pyca.db import get_session
from pyca.ui.utils import dtfmt, requires_auth
from pyca.utils import get_service_status
import os.path
app = Flask(__name__)
import pyca.ui.jsonapi  # noqa


@app.route('/')
@requires_auth
def home():
    '''Serve the status page of the capture agent.
    '''
    # Get IDs of existing preview images
    preview = config()['capture']['preview']
    previewdir = config()['capture']['preview_dir']
    preview = [p.replace('{{previewdir}}', previewdir) for p in preview]
    preview = zip(preview, range(len(preview)))
    preview = [p[1] for p in preview if os.path.isfile(p[0])]

    # Get limits for recording table
    try:
        limit_upcoming = int(request.args.get('limit_upcoming', 5))
        limit_processed = int(request.args.get('limit_processed', 15))
    except ValueError:
        limit_upcoming = 5
        limit_processed = 15

    db = get_session()
    upcoming_events = db.query(UpcomingEvent)\
                        .order_by(UpcomingEvent.start)\
                        .limit(limit_upcoming)
    recorded_events = db.query(RecordedEvent)\
                        .order_by(RecordedEvent.start.desc())\
                        .limit(limit_processed)
    recording = get_service_status(Service.CAPTURE) == ServiceStatus.BUSY
    uploading = get_service_status(Service.INGEST) == ServiceStatus.BUSY
    processed = db.query(RecordedEvent).count()
    upcoming = db.query(UpcomingEvent).count()

    return render_template('home.html', preview=preview, config=config(),
                           recorded_events=recorded_events,
                           upcoming_events=upcoming_events,
                           recording=recording, uploading=uploading,
                           processed=processed, upcoming=upcoming,
                           limit_upcoming=limit_upcoming,
                           limit_processed=limit_processed,
                           dtfmt=dtfmt)


@app.route("/img/<int:image_id>")
@requires_auth
def serve_image(image_id):
    '''Serve the preview image with the given id
    '''
    try:
        preview_dir = config()['capture']['preview_dir']
        filepath = config()['capture']['preview'][image_id]
        filepath = filepath.replace('{{previewdir}}', preview_dir)
        filepath = os.path.abspath(filepath)
        if os.path.isfile(filepath):
            directory, filename = filepath.rsplit('/', 1)
            return send_from_directory(directory, filename)
    except (IndexError, KeyError):
        pass
    return '', 404
