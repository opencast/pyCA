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
	{% endfor %}
</body>
</html>
'''


@app.route("/")
def home():

	# Check credentials:
	if config.UI_PASSWD and not request.authorization \
			or request.authorization.username != config.UI_USER \
			or request.authorization.password != config.UI_PASSWD:
		return Response('pyCA', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

	# Get IDs of existing preview images
	preview = [p % {'previewdir':config.PREVIEW_DIR} for p in config.CAPTURE_PREVIEW]
	preview = zip(preview, range(len(preview)))
	preview = [p[1] for p in preview if os.path.isfile(p[0])]

	template = Template(site)
	return template.render(preview=preview, refresh=config.UI_REFRESH_RATE)



@app.route("/img/<img>")
def img(img):
	'''Serve the preview image with the given id
	'''
	f = ''
	try:
		f = config.CAPTURE_PREVIEW[int(img)] % {'previewdir':config.PREVIEW_DIR}
		if os.path.isfile(f):
			[path,filename] = f.rsplit('/' , 1)
			return send_from_directory(path, filename)
	except:
		pass
	return '', 404
