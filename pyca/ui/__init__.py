# -*- coding: utf-8 -*-
'''
Simple UI telling about the current state of the capture agent.
'''
from pyca.config import config
from pyca.db import get_session, Status,  UpcomingEvent, RecordedEvent

import os.path
import datetime
from flask import Flask, request, send_from_directory, Response
from flask import render_template
app = Flask(__name__)


def dtfmt(ts):
    '''Covert Unix timestamp into human readable form
    '''
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


@app.route('/')
def home():
    '''Serve the status page of the capture agent.
    '''
    # Check credentials:
    if config()['ui']['password'] and not request.authorization \
            or request.authorization.username != config()['ui']['username'] \
            or request.authorization.password != config()['ui']['password']:
        return Response('pyCA', 401,
                        {'WWW-Authenticate': 'Basic realm="Login required"'})

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
    recording = db.query(RecordedEvent)\
                  .filter(RecordedEvent.status == Status.RECORDING)\
                  .count()
    uploading = db.query(RecordedEvent)\
                  .filter(RecordedEvent.status == Status.UPLOADING)\
                  .count()
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


@app.route("/img/<img>")
def serve_image(img):
    '''Serve the preview image with the given id
    '''
    filepath = ''
    try:
        preview_dir = config()['capture']['preview_dir']
        filepath = config()['capture']['preview'][int(img)]
        filepath = filepath.replace('{{previewdir}}', preview_dir)
        if os.path.isfile(filepath):
            [directory, filename] = filepath.rsplit('/', 1)
            return send_from_directory(directory, filename)
    except:
        pass
    return '', 404
