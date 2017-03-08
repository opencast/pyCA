# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import timestamp, try_mkdir, configure_service, ensurelist
from pyca.utils import register_ca, recording_state, update_event_status
from pyca.utils import terminate
from pyca.config import config
from pyca.db import get_session, RecordedEvent, UpcomingEvent, Status
import logging
import os
import os.path
import shlex
import signal
import subprocess
import sys
import time
import traceback


captureproc = None


def sigterm_handler(signum, frame):
    '''Intercept sigterm and terminate all processes.
    '''
    if captureproc and captureproc.poll() is None:
        captureproc.terminate()
    terminate(True)
    sys.exit(0)


def start_capture(event):
    '''Start the capture process, creating all necessary files and directories
    as well as ingesting the captured files if no backup mode is configured.
    '''
    logging.info('Start recording')

    # First move event to recording_event table
    db = get_session()
    events = db.query(RecordedEvent).filter(RecordedEvent.uid == event.uid)\
                                    .filter(RecordedEvent.start ==
                                            event.start)
    if events.count():
        event = events[0]
    else:
        event = RecordedEvent(event)
        db.add(event)
        db.commit()

    duration = event.end - timestamp()
    try_mkdir(config()['capture']['directory'])
    os.mkdir(event.directory())

    # Set state
    register_ca(status='capturing')
    recording_state(event.uid, 'capturing')
    update_event_status(event, Status.RECORDING)

    try:
        tracks = recording_command(event.directory(), event.name(), duration)
        event.set_tracks(tracks)
        db.commit()
    except:
        logging.error('Recording command failed')
        logging.error(traceback.format_exc())
        # Update state
        recording_state(event.uid, 'capture_error')
        update_event_status(event, Status.FAILED_RECORDING)
        register_ca(status='idle')
        return False

    register_ca(status='idle')
    update_event_status(event, Status.FINISHED_RECORDING)
    return True


def safe_start_capture(event):
    '''Start a capture process but make sure to catch any errors during this
    process, log them but otherwise ignore them.
    '''
    try:
        return start_capture(event)
    except Exception:
        logging.error('Start capture failed')
        logging.error(traceback.format_exc())
        recording_state(event.uid, 'capture_error')
        update_event_status(event, Status.FAILED_RECORDING)
        register_ca(status='idle')
        return False


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
    args = shlex.split(cmd)
    captureproc = subprocess.Popen(args)
    while captureproc.poll() is None:
        time.sleep(0.1)
    if captureproc.returncode > 0:
        raise Exception('Recording failed (%i)' % captureproc.returncode)

    # Remove preview files:
    for preview in config()['capture']['preview']:
        try:
            os.remove(preview.replace('{{previewdir}}', preview_dir))
        except OSError:
            logging.warning('Could not remove preview files')
            logging.warning(traceback.format_exc())

    # Return [(flavor,path),…]
    flavors = ensurelist(config()['capture']['flavors'])
    files = ensurelist(config()['capture']['files'])
    files = [f.replace('{{dir}}', directory) for f in files]
    files = [f.replace('{{name}}', name) for f in files]
    return list(zip(flavors, files))


def control_loop():
    '''Main loop of the capture agent, retrieving and checking the schedule as
    well as starting the capture process if necessry.
    '''
    while not terminate():
        # Get next recording
        register_ca()
        events = get_session().query(UpcomingEvent)\
                              .filter(UpcomingEvent.start <= timestamp())\
                              .filter(UpcomingEvent.end > timestamp())
        if events.count():
            safe_start_capture(events[0])
        time.sleep(1.0)
    logging.info('Shutting down capture service')


def run():
    '''Start the capture agent.
    '''
    signal.signal(signal.SIGTERM, sigterm_handler)
    configure_service('capture.admin')

    while not register_ca():
        time.sleep(5.0)

    control_loop()
    register_ca(status='unknown')
