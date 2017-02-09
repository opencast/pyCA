#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.config import config
from datetime import datetime
from dateutil.tz import tzutc
import errno
import json
import logging
import os
import os.path
import pycurl
import sys
import time
import traceback
if sys.version_info[0] == 2:
    from cStringIO import StringIO as bio
else:
    from io import BytesIO as bio


# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s ' +
                    '[%(filename)s:%(lineno)s:%(funcName)s()] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def http_request(url, post_data=None):
    '''Make an HTTP request to a given URL with optional parameters.
    '''
    buf = bio()
    curl = pycurl.Curl()
    curl.setopt(curl.URL, url.encode('ascii', 'ignore'))

    # Disable HTTPS verification methods if insecure is set
    if config()['server']['insecure']:
        curl.setopt(curl.SSL_VERIFYPEER, 0)
        curl.setopt(curl.SSL_VERIFYHOST, 0)

    if config()['server']['certificate']:
        # Make sure verification methods are turned on
        curl.setopt(curl.SSL_VERIFYPEER, 1)
        curl.setopt(curl.SSL_VERIFYHOST, 2)
        # Import your certificates
        curl.setopt(pycurl.CAINFO, config()['server']['certificate'])

    if post_data:
        curl.setopt(curl.HTTPPOST, post_data)
    curl.setopt(curl.WRITEFUNCTION, buf.write)
    curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
    curl.setopt(pycurl.USERPWD, "%s:%s" % (config()['server']['username'],
                                           config()['server']['password']))
    curl.setopt(curl.HTTPHEADER, ['X-Requested-Auth: Digest'])
    curl.perform()
    status = curl.getinfo(pycurl.HTTP_CODE)
    curl.close()
    if int(status / 100) != 2:
        raise Exception('Request to %s failed' % url, status)
    result = buf.getvalue()
    buf.close()
    return result


def get_service(service_type):
    '''Get available service endpoints for a given service type from the
    Opencast ServiceRegistry.
    '''
    endpoint = '/services/available.json?serviceType=' + str(service_type)
    url = '%s%s' % (config()['server']['url'], endpoint)
    response = http_request(url).decode('utf-8')
    services = (json.loads(response).get('services') or {}).get('service', [])
    # This will give us either a list or one element. Let us make sure, it is
    # a list
    try:
        services.get('type')
        services = [services]
    except AttributeError:
        pass
    endpoints = [s['host'] + s['path'] for s in services
                 if s['online'] and s['active']]
    for endpoint in endpoints:
        logging.info('Endpoint for %s: %s', service_type, endpoint)
    return endpoints


def unix_ts(dtval):
    '''Convert datetime into a unix timestamp.

    :param dt: datetime to convert
    '''
    epoch = datetime(1970, 1, 1, 0, 0, tzinfo=tzutc())
    delta = (dtval - epoch)
    return delta.days * 24 * 3600 + delta.seconds


def timestamp():
    '''Get current unix timestamp
    '''
    if config()['agent']['ignore_timezone']:
        return unix_ts(datetime.now())
    return unix_ts(datetime.now(tzutc()))


def try_mkdir(directory):
    '''Try to create a directory. Pass without error if it already exists.
    '''
    try:
        os.mkdir(directory)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise err


def configure_service(service):
    '''Get the location of a given service from Opencast and add it to the
    current configuration.
    '''
    while (not config().get('service-' + service)):
        try:
            config()['service-' + service] = \
                get_service('org.opencastproject.' + service)
        except:
            logging.error('Could not get %s endpoint. Retrying in 5 seconds' %
                          service)
            logging.error(traceback.format_exc())
        time.sleep(5.0)


def ensurelist(x):
    '''Ensure an element is a list.'''
    return x if type(x) == list else [x]
