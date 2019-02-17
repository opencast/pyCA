# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import http_request, configure_service, unix_ts, timestamp, \
                       set_service_status_immediate, terminate
from pyca.config import config
from pyca.db import get_session, UpcomingEvent, Service, ServiceStatus
from base64 import b64decode
from datetime import datetime
import dateutil.parser
import logging
import pycurl
import sdnotify
import sys
import time
import traceback
if sys.version_info[0] == 2:
    from urllib import urlencode
else:
    from urllib.parse import urlencode

logger = logging.getLogger(__name__)
notify = sdnotify.SystemdNotifier()


def parse_ical(vcal):
    '''Parse Opencast schedule iCalendar file and return events as dict
    '''
    vcal = vcal.replace('\r\n ', '').replace('\r\n\r\n', '\r\n')
    vevents = vcal.split('\r\nBEGIN:VEVENT\r\n')
    del(vevents[0])
    events = []
    for vevent in vevents:
        event = {}
        for line in vevent.split('\r\n'):
            line = line.split(':', 1)
            key = line[0].lower()
            if len(line) <= 1 or key == 'end':
                continue
            if key.startswith('dt'):
                event[key] = unix_ts(dateutil.parser.parse(line[1]))
                continue
            if not key.startswith('attach'):
                event[key] = line[1]
                continue
            # finally handle attachments
            event['attach'] = event.get('attach', [])
            attachment = {}
            for x in [x.split('=') for x in line[0].split(';')]:
                if x[0].lower() in ['fmttype', 'x-apple-filename']:
                    attachment[x[0].lower()] = x[1]
            attachment['data'] = b64decode(line[1]).decode('utf-8')
            event['attach'].append(attachment)
        events.append(event)
    return events


def get_schedule():
    '''Try to load schedule from the Matterhorn core. Returns a valid schedule
    or None on failure.
    '''
    params = {'agentid': config()['agent']['name'].encode('utf8')}
    lookahead = config()['agent']['cal_lookahead'] * 24 * 60 * 60
    if lookahead:
        params['cutoff'] = str((timestamp() + lookahead) * 1000)
    uri = '%s/calendars?%s' % (config()['service-scheduler'][0],
                               urlencode(params))
    try:
        vcal = http_request(uri)
    except pycurl.error as e:
        logger.error('Could not get schedule: %s' % e)
        return

    try:
        cal = parse_ical(vcal.decode('utf-8'))
    except Exception:
        logger.error('Could not parse ical')
        logger.error(traceback.format_exc())
        return
    db = get_session()
    db.query(UpcomingEvent).delete()
    for event in cal:
        # Ignore events that have already ended
        if event['dtend'] <= timestamp():
            continue
        e = UpcomingEvent()
        e.start = event['dtstart']
        e.end = event['dtend']
        e.uid = event.get('uid')
        e.title = event.get('summary')
        e.set_data(event)
        db.add(e)
    db.commit()


def control_loop():
    '''Main loop, retrieving the schedule.
    '''
    set_service_status_immediate(Service.SCHEDULE, ServiceStatus.BUSY)
    notify.notify('READY=1')
    while not terminate():
        notify.notify('WATCHDOG=1')
        # Try getting an updated schedule
        get_schedule()
        session = get_session()
        next_event = session.query(UpcomingEvent)\
                            .filter(UpcomingEvent.end > timestamp())\
                            .order_by(UpcomingEvent.start)\
                            .first()
        if next_event:
            logger.info('Next scheduled recording: %s',
                        datetime.fromtimestamp(next_event.start))
            notify.notify('STATUS=Next scheduled recording: %s' %
                          datetime.fromtimestamp(next_event.start))
        else:
            logger.info('No scheduled recording')
            notify.notify('STATUS=No scheduled recording')
        session.close()

        next_update = timestamp() + config()['agent']['update_frequency']
        while not terminate() and timestamp() < next_update:
            time.sleep(0.1)

    logger.info('Shutting down schedule service')
    set_service_status_immediate(Service.SCHEDULE, ServiceStatus.STOPPED)


def run():
    '''Start the capture agent.
    '''
    configure_service('scheduler')
    control_loop()
