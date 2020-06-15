# -*- coding: utf-8 -*-
'''
Helper methods used for the web interface.
'''

from functools import wraps
from flask import request, Response
from pyca.config import config


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if config('ui', 'password') and not auth \
                or auth.username != config('ui', 'username') \
                or auth.password != config('ui', 'password'):
            return Response('pyCA: Login required\n', 401,
                            {'WWW-Authenticate': 'Basic realm="pyCA Login"'})
        return f(*args, **kwargs)
    return decorated


def jsonapi_mediatype(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get('Content-Type') != 'application/vnd.api+json'\
                and request.method != 'GET':
            return Response('Unsupported Media Type '
                            '(expected: application/vnd.api+json)', 415)
        response = f(*args, **kwargs)
        response.headers['Content-Type'] = 'application/vnd.api+json'
        return response
    return decorated
