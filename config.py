#!/bin/env python
# -*- coding: utf-8 -*-
import os

CAPTURE_AGENT_NAME  = 'PyCA'
IGNORE_TZ           = False
ADMIN_SERVER_URL    = 'http://example.com:8080'
ADMIN_SERVER_USER   = 'matterhorn_system_account'
ADMIN_SERVER_PASSWD = 'CHANGE_ME'
UPDATE_FREQUENCY    = 60
CAPTURE_DIR         = '%s/recordings' % os.path.dirname(os.path.abspath(__file__))
CAPTURE_PLUGIN      = 'ffmpeg-v4l-alsa'

# Setting this to true will cause the pyCA to not register itself or ingest
# stuff to the admin server. It's useful if you want it as cbackup to another
# CA to just get the files manually if the regular CA fails.
BACKUP_AGENT        = False
