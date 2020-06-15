# -*- coding: utf-8 -*-
'''
Simple UI telling about the current state of the capture agent.
'''
from flask import Flask, send_from_directory, redirect, url_for
from pyca.config import config
from pyca.ui.utils import requires_auth
import os.path

__base_dir__ = os.path.abspath(os.path.dirname(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(__base_dir__, 'templates'),
    static_folder=os.path.join(__base_dir__, 'static'))
import pyca.ui.jsonapi  # noqa


@app.route('/')
@requires_auth
def home():
    '''Serve the status page of the capture agent.
    '''
    refresh_rate = config('ui', 'refresh_rate')

    return redirect(url_for(
        'static', filename='index.html', refresh=refresh_rate))


@app.route("/img/<int:image_id>")
@requires_auth
def serve_image(image_id):
    '''Serve the preview image with the given id
    '''
    try:
        preview_dir = config('capture', 'preview_dir')
        filepath = config('capture', 'preview')[image_id]
        filepath = filepath.replace('{{previewdir}}', preview_dir)
        filepath = os.path.abspath(filepath)
        if os.path.isfile(filepath):
            directory, filename = filepath.rsplit('/', 1)
            response = send_from_directory(directory, filename)
            response.cache_control.no_cache = True
            return response
    except (IndexError, KeyError):
        pass
    return '', 404
