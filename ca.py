#!/bin/env python
# -*- coding: utf-8 -*-
'''
	python-matterhorn-ca
	~~~~~~~~~~~~~~~~~~~~

	:copyright: 2013, Lars Kiesow <lkiesow@uos.de>
	:license: LGPL – see license.lgpl for more details.
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

import config


def get_url_opener():
	mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
	mgr.add_password(None, config.ADMIN_SERVER_URL, config.ADMIN_SERVER_USER,
			config.ADMIN_SERVER_PASSWD)
	return urllib2.build_opener(urllib2.HTTPBasicAuthHandler(mgr),
			urllib2.HTTPDigestAuthHandler(mgr))



def register_ca(address='http://localhost:8080',status='idle'):
	# If this is a backup CA we don't tell the Matterhorn core that we are here.
	# We will just run silently in the background:
	if config.BACKUP_AGENT:
		return
	params = {'address':address, 'state':status}
	req = urllib2.Request('%s/capture-admin/agents/%s' % (
			config.ADMIN_SERVER_URL, config.CAPTURE_AGENT_NAME),
			urllib.urlencode(params))
	req.add_header('X-Requested-Auth', 'Digest')

	u = get_url_opener().open(req)
	print u.read()
	u.close()


def recording_state(rid, status='upcoming'):
	# If this is a backup CA we don't update the recording state. The actual CA
	# does that and we don't want to mess with it.  We will just run silently in
	# the background:
	if config.BACKUP_AGENT:
		return
	params = {'state':status}
	req = urllib2.Request('%s/capture-admin/recordings/%s' % \
			(config.ADMIN_SERVER_URL, rid),
			urllib.urlencode(params))
	req.add_header('X-Requested-Auth', 'Digest')

	u = get_url_opener().open(req)
	print u.read()
	u.close()


def get_schedule():
	req = urllib2.Request('%s/recordings/calendars?agentid=%s' % (
			config.ADMIN_SERVER_URL, config.CAPTURE_AGENT_NAME))
	req.add_header('X-Requested-Auth', 'Digest')

	try:
		u = get_url_opener().open(req)
		vcal = u.read()
	except Exception as e:
		sys.stderr.write('Error: Could not get schedule')
		sys.stderr.write(' --> %s' % e.message)
		return
	finally:
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
	if config.IGNORE_TZ:
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


def start_capture(schedule):
	now = get_timestamp()
	print '%i: start_recording...' % now
	duration = schedule[1] - now
	recording_id = schedule[2]
	recording_name = 'recording-%s-%i' % (recording_id, now)
	recording_dir  = '%s/%s' % (config.CAPTURE_DIR, recording_name)
	os.mkdir(recording_dir)

	# Set state
	register_ca(status='capturing')
	recording_state(recording_id,'capturing')

	tracks = []
	try:
		tracks = recording_command(recording_dir, recording_name, duration)
	except Exception as e:
		print str(e)
		# Update state
		recording_state(recording_id,'capture_error')
		register_ca(status='idle')
		return False

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

	# If we are a backup CA, we don't want to actually upload anything. So let's
	# just quit here.
	if config.BACKUP_AGENT:
		return True

	# Upload everything
	register_ca(status='uploading')
	recording_state(recording_id,'uploading')

	rec_data = {
			'user':config.ADMIN_SERVER_USER,
			'passwd':config.ADMIN_SERVER_PASSWD,
			'url':config.ADMIN_SERVER_URL,
			'rec_dir':recording_dir,
			'rec_name':recording_name,
			'rec_id':recording_id,
			'workflow_def':workflow_def,
			'workflow_config':workflow_config }

	try:
		# create mediapackage
		curlcmd = ('curl -f --digest -u %(user)s:%(passwd)s ' \
				+ '-H "X-Requested-Auth: Digest" ' \
				+ '"%(url)s/ingest/createMediaPackage" ' \
				+ '-o "%(rec_dir)s/mediapackage.xml"') % rec_data
		print curlcmd
		if os.system(curlcmd):
			raise Exception('curl failed: Tried to create Mediapackage')

		# add episode dc catalog
		if os.path.isfile('%s/episode.xml' % recording_dir):
			curlcmd = ('curl -f --digest -u %(user)s:%(passwd)s ' \
					+ '-H "X-Requested-Auth: Digest" "%(url)s/ingest/addDCCatalog" ' \
					+ '-F "mediaPackage=<%(rec_dir)s/mediapackage.xml" ' \
					+ '-F "flavor=dublincore/episode" ' \
					+ '-F "dublinCore=@%(rec_dir)s/episode.xml" ' \
					+ '-o "%(rec_dir)s/mediapackage-new.xml"') % rec_data
			print curlcmd
			if os.system(curlcmd):
				raise Exception('curl failed: Tried to add episode DC catalog')
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
			if os.system(curlcmd):
				raise Exception('curl failed: Tried to add series DC catalog')
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
			if os.system(curlcmd):
				raise Exception('curl failed: Tried to upload track')
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
		if os.system(curlcmd):
			raise Exception('curl failed: Tried to ingest')

	except:
		# Update state if something went wrong
		recording_state(recording_id,'upload_error')
		register_ca(status='idle')
		return False

	# Update state
	recording_state(recording_id,'upload_finished')
	register_ca(status='idle')
	return True


def safe_start_capture(schedule):
	try:
		return start_capture(schedule)
	except Exception as e:
		print str(e)
		register_ca(status='idle')
		return False


def control_loop():
	last_update = 0
	schedule = []
	while True:
		if len(schedule) and schedule[0][0] <= get_timestamp():
			if not safe_start_capture(schedule[0]):
				# Something went wrong but we do not want to restart the capture
				# continuously
				time.sleep( schedule[0][1] - get_timestamp() )
		if get_timestamp() - last_update > config.UPDATE_FREQUENCY:
			schedule = get_schedule()
			last_update = get_timestamp()
			#print '%i: updated schedule' % get_timestamp()
			#print ' > starting timestamps: ', [ x[0] for x in schedule ]
			if schedule:
				print 'Next scheduled recording: %s' % datetime.fromtimestamp(schedule[0][0])
			else:
				print 'No scheduled recording'
		time.sleep(1.0)


def load_capture_plugin():
	import imp
	mod = imp.load_source('capture', '%s/capture_plugins/%s.py' % (
		os.path.dirname(os.path.abspath(__file__)),
		config.CAPTURE_PLUGIN ))
	global recording_command
	recording_command = mod.recording_command
	if recording_command:
		print 'Found recording plug-in'


if __name__ == '__main__':
	load_capture_plugin()
	register_ca()
	get_schedule()
	control_loop()
