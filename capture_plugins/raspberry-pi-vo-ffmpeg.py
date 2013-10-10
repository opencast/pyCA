#!/bin/env python
# -*- coding: utf-8 -*-
'''
	python-matterhorn-ca
	~~~~~~~~~~~~~~~~~~~~

	This recording plugin will record an H264 video stream from the Raspberry Pi
	camera board and pack this into an Mp4 container using FFmpeg. No audio will
	be recorded.

	:copyright: 2013, Lars Kiesow <lkiesow@uos.de>
	:license: LGPL – see license.lgpl for more details.
'''

import os

def recording_command(rec_dir, rec_name, rec_duration):
	rec_path = '%s/%s.mp4' % (rec_dir,rec_name)
	rec_cmd = '''raspivid -n -t %i000 -b 4000000 -fps 30 -o - | \
			ffmpeg -r 30 -i pipe:0 -c:v copy \
			-y %s''' % ( rec_duration, rec_path )
	print rec_cmd
	if os.system(rec_cmd):
		raise Exception('Recording failed')
	return [ ('presenter/source', rec_path) ]
