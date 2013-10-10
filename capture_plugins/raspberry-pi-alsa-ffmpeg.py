#!/bin/env python
# -*- coding: utf-8 -*-
'''
	python-matterhorn-ca
	~~~~~~~~~~~~~~~~~~~~

	This recording plugin will record an H264 video stream from the Raspberry Pi
	camera board and a audio stream from an ALSA device. The audio will be
	encoded using the Flac lossless audio codec. The container format which hold
	these streams is a Matroska container.

	:copyright: 2013, Lars Kiesow <lkiesow@uos.de>
	:license: LGPL – see license.lgpl for more details.
'''

import os

def recording_command(rec_dir, rec_name, rec_duration):
	rec_path = '%s/%s.mkv' % (rec_dir,rec_name)
	rec_cmd = '''raspivid -t %i000 -b 4000000 -fps 30 -o - | \
			ffmpeg -ac 1 -f alsa -i plughw:1 \
			-r 25 -i pipe:0 \
			-filter:a aresample=async=1 \
			-c:a flac -c:v copy \
			-t %i -y %s''' % ( rec_duration, rec_duration, rec_path )
	print rec_cmd
	if os.system(rec_cmd):
		raise Exception('Recording failed')
	return [ ('presenter/source', rec_path) ]
