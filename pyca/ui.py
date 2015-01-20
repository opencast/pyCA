#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

from pyca import config

import os.path
from jinja2 import Template
from flask import Flask, render_template, request, send_from_directory, Response
app = Flask(__name__)

site = '''
<!doctype html>
<html>
<head>
	<meta http-equiv="refresh" content="{{ refresh }}; URL=/">
	<title>pyCA</title>
</head>
<body style="text-align: center;">
	{% for p in preview %}
		<img style="max-width: 90%;" src="/img/{{ p }}" />
	{% else %}
		The capture agent is currently not recording.
	{% endfor %}
</body>
</html>
'''


def update_configuration(cfgfile):
	'''Update configuration from file.

	:param cfgfile: Configuration file to load.
	'''
	global config
	from configobj import ConfigObj
	from pyca.config import cfgspec
	from validate import Validator
	config = ConfigObj(cfgfile, configspec=cfgspec)
	validator = Validator()
	config.validate(validator)
	return config


# Set up configuration
config = update_configuration('/etc/pyca.conf')


@app.route('/')
def home():

	# Check credentials:
	if config['ui']['password'] and not request.authorization \
			or request.authorization.username != config['ui']['username'] \
			or request.authorization.password != config['ui']['password']:
		return Response('pyCA', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

	# Get IDs of existing preview images
	preview = config['capture']['preview']
	previewdir = config['capture']['preview_dir']
	preview = [p.replace('{{previewdir}}', previewdir) for p in preview]
	preview = zip(preview, range(len(preview)))
	preview = [p[1] for p in preview if os.path.isfile(p[0])]

	template = Template(site)
	return template.render(preview=preview, refresh=config['ui']['refresh_rate'])



@app.route("/img/<img>")
def img(img):
	'''Serve the preview image with the given id
	'''
	f = ''
	try:
		f = config['capture']['preview'][int(img)].replace('{{previewdir}}', config['capture']['preview_dir'])
		if os.path.isfile(f):
			[path,filename] = f.rsplit('/' , 1)
			return send_from_directory(path, filename)
	except:
		pass
	return '', 404
