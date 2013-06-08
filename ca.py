#!/bin/env python
# -*- coding: utf-8 -*-
'''
	python-matterhorn-ca
	~~~~~~~~~~~~~~~~~~~~

	:copyright: 2013, Lars Kiesow <lkiesow@uos.de>
	:license: FreeBSD and LGPL, see license.* for more details.
'''

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
import time
import urllib
import urllib2
import dateutil.tz
from xml.dom.minidom import parseString
from base64 import b64decode
import logging
import icalendar
from datetime import datetime
import os.path

ignore_tz = False
admin_server_url    = 'http://localhost:8080'
admin_server_user   = 'digestadmin'
admin_server_passwd = 'opencast'
update_frequency    = 60
capture_dir         = '/home/pi/recordings/'


def get_url_opener():
	mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
	mgr.add_password(None, admin_server_url, admin_server_user,
			admin_server_passwd)
	return urllib2.build_opener(urllib2.HTTPBasicAuthHandler(mgr),
			urllib2.HTTPDigestAuthHandler(mgr))



def register_ca(address='http://localhost:8080',status='idle'):
	params = {'address':address, 'state':status}
	req = urllib2.Request('%s/capture-admin/agents/pica' % admin_server_url,
			urllib.urlencode(params))
	req.add_header('X-Requested-Auth', 'Digest')

	u = get_url_opener().open(req)
	print u.read()
	u.close()


def recording_state(rid, status='upcoming'):
	params = {'state':status}
	req = urllib2.Request('%s/capture-admin/recordings/%s' % \
			(admin_server_url, rid),
			urllib.urlencode(params))
	req.add_header('X-Requested-Auth', 'Digest')

	u = get_url_opener().open(req)
	print u.read()
	u.close()


def get_schedule():
	req = urllib2.Request('%s/recordings/calendars?agentid=pica' % \
			admin_server_url)
	req.add_header('X-Requested-Auth', 'Digest')

	u = get_url_opener().open(req)
	vcal = u.read()
	u.close()

	cal = None
	try:
		cal = icalendar.Calendar.from_string(vcal)
	except:
		cal = icalendar.Calendar.from_ical(vcal)
	events = []
	for event in cal.walk('vevent'):
		dtstart = unix_ts(event.get('dtstart').dt.astimezone(dateutil.tz.tzutc()))
		dtend   = unix_ts(event.get('dtend').dt.astimezone(dateutil.tz.tzutc()))
		uid     = event.get('uid').decode()

		# Ignore events that have already ended
		if dtend > get_timestamp():
			events.append( (dtstart,dtend,uid,event) )

	return sorted(events, key=lambda x: x[0])


def unix_ts(dt):
	epoch = datetime(1970, 1, 1, 0, 0, tzinfo = dateutil.tz.tzutc())
	delta = (dt - epoch)
	return delta.days * 24 * 3600 + delta.seconds


def get_timestamp():
	if ignore_tz:
		return unix_ts(datetime.now())
	return unix_ts(datetime.now(dateutil.tz.tzutc()))


def get_config_params(properties):
	param = ''
	wdef = 'full'
	for prop in properties.split('\n'):
		if prop.startswith('org.opencastproject.workflow.config'):
			k,v = prop.split('=',1)
			k = k.split('.')[-1]
			param += '-F "%s=%s" ' % (k, v)
		elif prop.startswith('org.opencastproject.workflow.definition'):
			wdef = prop.split('=',1)[-1]
	return wdef, param


def default_recording_command(rec_dir, rec_name, rec_duration):
	rec_cmd = ('raspivid -t %(duration)i000 -n -b 4000000 -hf -vf -fps 25 -o - | ' \
			+ 'ffmpeg ' \
			+ '-f alsa -i hw:2 ' \
			+ '-r 25 -i pipe:0 -c:v copy -t %(duration)i ' \
			+ '"%(rec_dir)s/%(rec_name)s.mkv"') % \
			{ 'duration':rec_duration, 
				'rec_dir':rec_dir,
				'rec_name':rec_name}
	print rec_cmd
	os.system(rec_cmd)
	return [('presenter/source', '%s/%s.mkv' % (rec_dir,rec_name))]


recording_command   = default_recording_command


def start_capture(schedule):
	now = get_timestamp()
	print '%i: start_recording...' % now
	duration = schedule[1] - now
	recording_id = schedule[2]
	recording_name = 'recording-%s-%i' % (recording_id, now)
	recording_dir  = '%s/%s' % (capture_dir, recording_name)
	os.mkdir(recording_dir)

	# Set state
	register_ca(status='capturing')
	recording_state(recording_id,'capturing')

	'''
	rec_cmd = ('raspivid -t %(duration)i000 -n -vf -o - | ' \
			+ 'ffmpeg -i silence.mkv -acodec copy ' \
			+ '-r 30 -i pipe:0 -vcodec copy -t %(duration)i ' \
			+ '"%(rec_dir)s/%(rec_name)s.mkv"') % \
			{ 'duration':duration, 
				'rec_dir':recording_dir,
				'rec_name':recording_name}
	os.system(rec_cmd)
	'''
	tracks = recording_command(recording_dir, recording_name, duration)

	# Put metadata files on disk
	attachments = schedule[-1].get('attach')
	workflow_config=''
	for a in attachments:
		value = b64decode(a.decode())
		if value.startswith('<'):
			if '<dcterms:temporal>' in value:
				f = open('%s/episode.xml' % recording_dir, 'w')
				f.write(value)
				f.close()
			else:
				f = open('%s/series.xml' % recording_dir, 'w')
				f.write(value)
				f.close()
		else:
			workflow_def, workflow_config = get_config_params(value)
			f = open('%s/recording.properties' % recording_dir, 'w')
			f.write(value)
			f.close()

	# Upload everything
	register_ca(status='uploading')
	recording_state(recording_id,'uploading')
	
	rec_data = {
			'user':admin_server_user,
			'passwd':admin_server_passwd,
			'url':admin_server_url,
			'rec_dir':recording_dir,
			'rec_name':recording_name,
			'rec_id':recording_id,
			'workflow_def':workflow_def,
			'workflow_config':workflow_config }

	# create mediapackage
	curlcmd = ('curl -f --digest -u %(user)s:%(passwd)s ' \
			+ '-H "X-Requested-Auth: Digest" ' \
			+ '"%(url)s/ingest/createMediaPackage" ' \
			+ '-o "%(rec_dir)s/mediapackage.xml"') % rec_data
	print curlcmd
	os.system(curlcmd)

	# add episode dc catalog
	if os.path.isfile('%s/episode.xml' % recording_dir):
		curlcmd = ('curl -f --digest -u %(user)s:%(passwd)s ' \
				+ '-H "X-Requested-Auth: Digest" "%(url)s/ingest/addDCCatalog" ' \
				+ '-F "mediaPackage=<%(rec_dir)s/mediapackage.xml" ' \
				+ '-F "flavor=dublincore/episode" ' \
				+ '-F "dublinCore=@%(rec_dir)s/episode.xml" ' \
				+ '-o "%(rec_dir)s/mediapackage-new.xml"') % rec_data
		print curlcmd
		os.system(curlcmd)
		os.rename('%s/mediapackage-new.xml' % recording_dir,
				'%s/mediapackage.xml' % recording_dir)

	# add series dc catalog
	if os.path.isfile('%s/series.xml' % recording_dir):
		curlcmd = ('curl -f --digest -u %(user)s:%(passwd)s ' \
				+ '-H "X-Requested-Auth: Digest" "%(url)s/ingest/addDCCatalog" ' \
				+ '-F "mediaPackage=<%(rec_dir)s/mediapackage.xml" ' \
				+ '-F "flavor=dublincore/series" ' \
				+ '-F "dublinCore=@%(rec_dir)s/series.xml" ' \
				+ '-o "%(rec_dir)s/mediapackage-new.xml"') % rec_data
		print curlcmd
		os.system(curlcmd)
		os.rename('%s/mediapackage-new.xml' % recording_dir,
				'%s/mediapackage.xml' % recording_dir)

	# add track
	for (flavor, track) in tracks:
		track_data = rec_data.copy()
		track_data['flavor'] = flavor
		track_data['track']  = track
		curlcmd = ('curl -f --digest -u %(user)s:%(passwd)s ' \
				+ '-H "X-Requested-Auth: Digest" "%(url)s/ingest/addTrack" ' \
				+ '-F "flavor=%(flavor)s" ' \
				+ '-F "mediaPackage=<%(rec_dir)s/mediapackage.xml" ' \
				+ '-F "BODY1=@%(track)s" ' \
				+ '-o "%(rec_dir)s/mediapackage-new.xml"') % track_data
		print curlcmd
		os.system(curlcmd)
		os.rename('%s/mediapackage-new.xml' % recording_dir,
				'%s/mediapackage.xml' % recording_dir)

	# ingest
	curlcmd = ('curl -f --digest -u %(user)s:%(passwd)s ' \
			+ '-H "X-Requested-Auth: Digest" "%(url)s/ingest/ingest" ' \
			+ '-F "mediaPackage=<%(rec_dir)s/mediapackage.xml" ' \
			+ '-F "workflowDefinitionId=%(workflow_def)s" ' \
			+ '-F "workflowInstanceId=%(rec_id)s" ' \
			+ '%(workflow_config)s ' \
			+ '-o "%(rec_dir)s/worflowInstance.xml"') % rec_data
	print curlcmd
	os.system(curlcmd)

	# Update state
	recording_state(recording_id,'upload_finished')
	register_ca(status='idle')


def control_loop():
	last_update = 0
	schedule = []
	while True:
		if len(schedule) and schedule[0][0] <= get_timestamp():
			start_capture(schedule[0])
		if get_timestamp() - last_update > update_frequency:
			schedule = get_schedule()
			last_update = get_timestamp()
			print '%i: updated schedule' % get_timestamp()
			print ' > starting timestamps: ', [ x[0] for x in schedule ]
		time.sleep(1.0)


if __name__ == '__main__':
	register_ca()
	print get_schedule()
	control_loop()
