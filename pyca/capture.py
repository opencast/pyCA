# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import timestamp, try_mkdir, configure_service, ensurelist
from pyca.utils import set_service_status, set_service_status_immediate
from pyca.utils import recording_state, update_event_status, terminate
from pyca.config import config
from pyca.db import get_session, RecordedEvent, UpcomingEvent, Status,\
                    Service, ServiceStatus
import logging
import os
import os.path
import shlex
import signal
import subprocess
import sys
import time
import traceback

logger = logging.getLogger(__name__)
captureproc = None


def sigterm_handler(signum, frame):
    '''Intercept sigterm and terminate all processes.
    '''
    if captureproc and captureproc.poll() is None:
        captureproc.terminate()
    terminate(True)
    sys.exit(0)


def start_capture(upcoming_event):
    '''Start the capture process, creating all necessary files and directories
    as well as ingesting the captured files if no backup mode is configured.
    '''
    logger.info('Start recording')

    # First move event to recording_event table
    db = get_session()
    event = db.query(RecordedEvent)\
              .filter(RecordedEvent.uid == upcoming_event.uid)\
              .filter(RecordedEvent.start == upcoming_event.start)\
              .first()
    if not event:
        event = RecordedEvent(upcoming_event)
        db.add(event)
        db.commit()

    duration = event.end - timestamp()
    try_mkdir(config()['capture']['directory'])
    os.mkdir(event.directory())

    # Set state
    set_service_status_immediate(Service.CAPTURE, ServiceStatus.BUSY)
    recording_state(event.uid, 'capturing')
    update_event_status(event, Status.RECORDING)

    # Recording
    tracks = recording_command(event.directory(), event.name(), duration)
    event.set_tracks(tracks)
    db.commit()

    # Set status
    set_service_status_immediate(Service.CAPTURE, ServiceStatus.IDLE)
    update_event_status(event, Status.FINISHED_RECORDING)


def safe_start_capture(event):
    '''Start a capture process but make sure to catch any errors during this
    process, log them but otherwise ignore them.
    '''
    try:
        start_capture(event)
    except Exception:
        logger.error('Recording failed')
        logger.error(traceback.format_exc())
        # Update state
        recording_state(event.uid, 'capture_error')
        update_event_status(event, Status.FAILED_RECORDING)
        set_service_status_immediate(Service.CAPTURE, ServiceStatus.IDLE)


def recording_command(directory, name, duration):
    '''Run the actual command to record the a/v material.
    '''
    preview_dir = config()['capture']['preview_dir']
    cmd = config()['capture']['command']
    cmd = cmd.replace('{{time}}', str(duration))
    cmd = cmd.replace('{{dir}}', directory)
    cmd = cmd.replace('{{name}}', name)
    cmd = cmd.replace('{{previewdir}}', preview_dir)
    logger.info(cmd)
    args = shlex.split(cmd)
    DEVNULL = getattr(subprocess, 'DEVNULL', os.open(os.devnull, os.O_RDWR))
    captureproc = subprocess.Popen(args, stdin=DEVNULL)
    hasattr(subprocess, 'DEVNULL') or os.close(DEVNULL)
    while captureproc.poll() is None:
        time.sleep(0.1)
    if captureproc.returncode > 0:
        raise RuntimeError('Recording failed (%i)' % captureproc.returncode)

    # Remove preview files:
    for preview in config()['capture']['preview']:
        try:
            os.remove(preview.replace('{{previewdir}}', preview_dir))
        except OSError:
            logger.warning('Could not remove preview files')
            logger.warning(traceback.format_exc())

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
    set_service_status(Service.CAPTURE, ServiceStatus.IDLE)
    while not terminate():
        # Get next recording
        event = get_session().query(UpcomingEvent)\
                             .filter(UpcomingEvent.start <= timestamp())\
                             .filter(UpcomingEvent.end > timestamp())\
                             .first()
        if event:
            safe_start_capture(event)
        time.sleep(1.0)
    logger.info('Shutting down capture service')
    set_service_status(Service.CAPTURE, ServiceStatus.STOPPED)


def run():
    '''Start the capture agent.
    '''
    signal.signal(signal.SIGTERM, sigterm_handler)
    configure_service('capture.admin')
    control_loop()
