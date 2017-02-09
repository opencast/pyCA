#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import http_request, configure_service, unix_ts, timestamp
from pyca.config import config
from pyca.db import get_session, UpcomingEvent
from base64 import b64decode
from datetime import datetime
import dateutil.parser
import logging
import time
import traceback


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
    try:
        uri = '%s/calendars?agentid=%s' % (config()['service-scheduler'][0],
                                           config()['agent']['name'])
        lookahead = config()['agent']['cal_lookahead'] * 24 * 60 * 60
        if lookahead:
            uri += '&cutoff=%i' % ((timestamp() + lookahead) * 1000)
        vcal = http_request(uri)
    except Exception as e:
        # Silently ignore the error if the capture agent is not yet registered
        if e.args[1] != 404:
            logging.error('Could not get schedule')
            logging.error(traceback.format_exc())
        return

    try:
        cal = parse_ical(vcal.decode('utf-8'))
    except:
        logging.error('Could not parse ical')
        logging.error(traceback.format_exc())
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
        e.set_data(event)
        db.add(e)
    db.commit()


def control_loop():
    '''Main loop, retrieving the schedule.
    '''
    while True:
        # Try getting an updated schedult
        get_schedule()
        q = get_session().query(UpcomingEvent)\
                         .filter(UpcomingEvent.end > timestamp())
        if q.count():
            logging.info('Next scheduled recording: %s',
                         datetime.fromtimestamp(q[0].start))
        else:
            logging.info('No scheduled recording')
        time.sleep(config()['agent']['update_frequency'])


def run():
    '''Start the capture agent.
    '''
    configure_service('scheduler')
    try:
        control_loop()
    except KeyboardInterrupt:
        pass
