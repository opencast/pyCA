#!/bin/env python
# -*- coding: utf-8 -*-
import os

CAPTURE_AGENT_NAME  = 'PyCA'
IGNORE_TZ           = False
ADMIN_SERVER_URL    = 'http://localhost:8080'
ADMIN_SERVER_URL    = 'http://repo:8080'
ADMIN_SERVER_USER   = 'digestadmin'
ADMIN_SERVER_PASSWD = 'opencast'
UPDATE_FREQUENCY    = 60
CAPTURE_DIR         = '%s/recordings' % os.path.dirname(os.path.abspath(__file__))
CAPTURE_PLUGIN      = 'ffmpeg-v4l-alsa'
