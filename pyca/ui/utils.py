# -*- coding: utf-8 -*-
'''
Helper methods used for the web interface.
'''

import datetime
from functools import wraps
from flask import request, Response
from pyca.config import config


def dtfmt(ts):
    '''Covert Unix timestamp into human readable form
    '''
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if config()['ui']['password'] and not auth \
                or auth.username != config()['ui']['username'] \
                or auth.password != config()['ui']['password']:
            return Response('pyCA', 401,
                            {'WWW-Authenticate': 'Basic realm="pyCA Login"'})
        return f(*args, **kwargs)
    return decorated
