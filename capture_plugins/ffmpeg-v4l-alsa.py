#!/bin/env python
# -*- coding: utf-8 -*-
'''
	python-matterhorn-ca
	~~~~~~~~~~~~~~~~~~~~

	:copyright: 2013, Lars Kiesow <lkiesow@uos.de>
	:license: LGPL – see license.lgpl for more details.
'''

import os

def recording_command(rec_dir, rec_name, rec_duration):
	rec_cmd = '''ffmpeg -f v4l2 -s 1280x720 -i /dev/video1 \
			-f alsa -ac 1 -i hw:1 -filter:a aresample=async=1000 \
			-t %i -c:a:0 flac -ac 1 \
			-c:v:0 libx264 -preset ultrafast -qp 0 \
			-y %s/%s.mkv''' % ( rec_duration, rec_dir, rec_name)
	print rec_cmd
	if os.system(rec_cmd):
		raise Exception('Recording failed')
	return [('presenter/source', '%s/%s.mkv' % (rec_dir,rec_name))]
