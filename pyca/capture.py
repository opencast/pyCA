# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import timestamp, try_mkdir, terminate
from pyca.utils import set_service_status, set_service_status_immediate
from pyca.utils import recording_state, update_event_status
from pyca.config import config
from pyca.db import get_session, RecordedEvent, UpcomingEvent, Status,\
                    Service, ServiceStatus, with_session
import glob
import logging
import os
import os.path
import sdnotify
import shlex
import signal
import subprocess
import sys
import time

logger = logging.getLogger(__name__)
notify = sdnotify.SystemdNotifier()
captureproc = None


def sigterm_handler(signum, frame):
    '''Intercept sigterm and terminate all processes.
    '''
    if captureproc and captureproc.poll() is None:
        captureproc.terminate()
    terminate(True)
    sys.exit(0)


@with_session
def start_capture(db, upcoming_event):
    '''Start the capture process, creating all necessary files and directories
    as well as ingesting the captured files if no backup mode is configured.
    '''
    logger.info('Start recording')

    # First move event to recording_event table
    event = db.query(RecordedEvent)\
              .filter(RecordedEvent.uid == upcoming_event.uid)\
              .filter(RecordedEvent.start == upcoming_event.start)\
              .first()
    if not event:
        event = RecordedEvent(upcoming_event)
        db.add(event)
        db.commit()

    try_mkdir(config('capture', 'directory'))
    try_mkdir(event.directory())

    # Set state
    update_event_status(event, Status.RECORDING)
    recording_state(event.uid, 'capturing')
    set_service_status_immediate(Service.CAPTURE, ServiceStatus.BUSY)

    # Recording
    files = recording_command(event)
    # [(flavor,path),…]
    event.set_tracks(list(zip(config('capture', 'flavors'), files)))
    db.commit()

    # Set status
    # If part files exist, its an partial recording
    part_files = any([glob.glob(f'{f}-part-*') for f in files])
    if part_files:
        state = Status.PARTIAL_RECORDING
    elif config('agent', 'backup_mode'):
        state = Status.PAUSED_AFTER_RECORDING
    else:
        state = Status.FINISHED_RECORDING

    logger.info("Set %s to %s", event.uid, Status.str(state))
    update_event_status(event, state)
    recording_state(event.uid, 'capture_finished')
    set_service_status_immediate(Service.CAPTURE, ServiceStatus.IDLE)

    logger.info('Finished recording')


def safe_start_capture(event):
    '''Start a capture process but make sure to catch any errors during this
    process, log them but otherwise ignore them.
    '''
    try:
        start_capture(event)
    except Exception:
        logger.exception('Recording failed')
        # Update current status in Opencast
        try:
            set_service_status_immediate(Service.CAPTURE, ServiceStatus.IDLE)
            recording_state(event.uid, 'capture_error')
            update_event_status(event, Status.FAILED_RECORDING)
        except Exception:
            logger.exception('Could not update recording status')


def recording_command(event):
    '''Run the actual command to record the a/v material.
    '''
    conf = config('capture')
    # Prepare command line
    cmd = conf['command']
    cmd = cmd.replace('{{time}}', str(event.remaining_duration(timestamp())))
    cmd = cmd.replace('{{dir}}', event.directory())
    cmd = cmd.replace('{{name}}', event.name())
    cmd = cmd.replace('{{previewdir}}', conf['preview_dir'])

    # Parse files into list
    files = (f.replace('{{dir}}', event.directory()) for f in conf['files'])
    files = [f.replace('{{name}}', event.name()) for f in files]

    # Move existing files from previous failed recordings
    for f in files:
        if not os.path.exists(f):
            continue
        # New filename
        i = 0
        while True:
            new_filename = f'{f}-part-{i}'
            if not os.path.exists(new_filename):
                break
            i += 1
        # Move file
        os.rename(f, new_filename)
        logger.warning("Moved file %s to %s to keep it", f, new_filename)

    # Signal configuration
    sigterm_time = conf['sigterm_time']
    sigkill_time = conf['sigkill_time']
    sigcustom_time = conf['sigcustom_time']
    sigcustom_time = 0 if sigcustom_time < 0 else event.end + sigcustom_time
    sigterm_time = 0 if sigterm_time < 0 else event.end + sigterm_time
    sigkill_time = 0 if sigkill_time < 0 else event.end + sigkill_time

    # Launch capture command
    logger.info(cmd)
    args = shlex.split(cmd)
    DEVNULL = getattr(subprocess, 'DEVNULL', os.open(os.devnull, os.O_RDWR))
    captureproc = subprocess.Popen(args, stdin=DEVNULL)
    hasattr(subprocess, 'DEVNULL') or os.close(DEVNULL)

    # Set systemd status
    notify.notify('STATUS=Capturing')

    # Check process
    while captureproc.poll() is None:
        notify.notify('WATCHDOG=1')
        if sigcustom_time and timestamp() > sigcustom_time:
            logger.info("Sending custom signal to capture process")
            captureproc.send_signal(conf['sigcustom'])
            sigcustom_time = 0  # send only once
        if sigterm_time and timestamp() > sigterm_time:
            logger.info("Terminating capture process")
            captureproc.terminate()
            sigterm_time = 0  # send only once
        elif sigkill_time and timestamp() > sigkill_time:
            logger.warning("Killing capture process")
            captureproc.kill()
            sigkill_time = 0  # send only once
        time.sleep(0.1)

    # Remove preview files:
    for preview in conf['preview']:
        try:
            os.remove(preview.replace('{{previewdir}}', conf['preview_dir']))
        except OSError:
            logger.warning('Could not remove preview files', exc_info=True)

    # Check process for errors
    exitcode = conf['exit_code']
    if captureproc.poll() > 0 and captureproc.returncode != exitcode:
        raise RuntimeError('Recording failed (%i)' % captureproc.returncode)

    # Reset systemd status
    notify.notify('STATUS=Waiting')

    # files
    return files


def control_loop():
    '''Main loop of the capture agent, retrieving and checking the schedule as
    well as starting the capture process if necessry.
    '''
    set_service_status_immediate(Service.CAPTURE, ServiceStatus.IDLE)
    notify.notify('READY=1')
    notify.notify('STATUS=Waiting')
    while not terminate():
        notify.notify('WATCHDOG=1')
        # Get next recording
        session = get_session()
        event = session.query(UpcomingEvent)\
                       .filter(UpcomingEvent.start <= timestamp())\
                       .filter(UpcomingEvent.end > timestamp())\
                       .first()
        if event:
            safe_start_capture(event)
        session.close()
        time.sleep(1.0)
    logger.info('Shutting down capture service')
    set_service_status(Service.CAPTURE, ServiceStatus.STOPPED)


def run():
    '''Start the capture agent.
    '''
    signal.signal(signal.SIGTERM, sigterm_handler)
    control_loop()
