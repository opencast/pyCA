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
	rec_path = '%s/%s.flac' % (rec_dir,rec_name)
	rec_cmd = '''ffmpeg -ac 2 -f alsa -i hw:0 -c:a flac \
			-t %i -y %s''' % ( rec_duration, rec_path )
	print rec_cmd
	if os.system(rec_cmd):
		raise Exception('Recording failed')
	return [ ('presenter/source', rec_path) ]
