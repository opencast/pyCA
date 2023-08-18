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
        headers = {'WWW-Authenticate': 'Basic realm="pyCA Login"'}
        auth = request.authorization
        if config('ui', 'password'):
            auth_provided = (auth.username, auth.password) if auth else None
            auth_expected = config('ui', 'username'), config('ui', 'password')
            if auth_provided != auth_expected:
                return Response('pyCA: Login required\n', 401, headers)
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
