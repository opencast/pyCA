# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2022, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from xml.sax.saxutils import escape as xml_escape  # nosec B406
from pyca.config import config
from pyca.utils import http_request, service
from datetime import datetime, timedelta
import logging
import random

logger = logging.getLogger(__name__)

DUBLINCORE = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<dublincore xmlns="http://www.opencastproject.org/xsd/1.0/dublincore/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dcterms:creator>{creator}</dcterms:creator>
  <dcterms:created xsi:type="dcterms:W3CDTF">{start}</dcterms:created>
  <dcterms:temporal xsi:type="dcterms:Period">start={start}; end={end}; scheme=W3C-DTF;</dcterms:temporal>
  <dcterms:language>demo</dcterms:language>
  <dcterms:spatial>{agent_name}</dcterms:spatial>
  <dcterms:title>{title}</dcterms:title>
</dublincore>'''  # noqa


def schedule(title='pyCA Recording', duration=60, creator=None):
    '''Schedule a recording for this capture agent with the given title,
    creator and duration starting 10 seconds from now.

    :param title: Title of the event to schedule
    :type title: string
    :param creator: Creator of the event to schedule
    :type creator: string
    :param duration: Duration of the event to schedule in seconds
    :type creator: int
    '''
    if not creator:
        creator = config('ui', 'username')

    # Select ingest service
    # The ingest service to use is selected at random from the available
    # ingest services to ensure that not every capture agent uses the same
    # service at the same time
    service_url = service('ingest', force_update=True)
    service_url = service_url[random.randrange(0, len(service_url))]  # nosec
    logger.info('Selecting ingest service for scheduling: ' + service_url)

    # create media package
    logger.info('Creating new media package')
    mediapackage = http_request(service_url + '/createMediaPackage', timeout=0)

    # add dublin core catalog
    start = datetime.utcnow() + timedelta(seconds=10)
    end = start + timedelta(seconds=duration)
    dublincore = DUBLINCORE.format(
            agent_name=xml_escape(config('agent', 'name')),
            start=start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            end=end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            title=xml_escape(title),
            creator=xml_escape(creator))
    logger.info('Adding Dublin Core catalog for scheduling')
    fields = [('mediaPackage', mediapackage),
              ('flavor', 'dublincore/episode'),
              ('dublinCore', dublincore)]
    mediapackage = http_request(service_url + '/addDCCatalog', fields,
                                timeout=0)

    # schedule event
    logger.info('Scheduling recording')
    fields = [('mediaPackage', mediapackage)]
    mediapackage = http_request(service_url + '/schedule', fields, timeout=0)

    # Update status
    logger.info('Event successfully scheduled')
