#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
	python-matterhorn-ca
	~~~~~~~~~~~~~~~~~~~~

	:copyright: 2014-2015, Lars Kiesow <lkiesow@uos.de>
	:license: LGPL – see license.lgpl for more details.
'''

# Set default encoding to UTF-8
import sys
import os
import time
import pycurl
import dateutil.tz
from base64 import b64decode
import logging
import icalendar
from datetime import datetime
import os.path
if sys.version_info[0] == 2:
	from cStringIO import StringIO as bio
else:
	from io import BytesIO as bio
import traceback


# Set up logging
logging.basicConfig(level=logging.INFO,
		format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)s:%(funcName)s()] %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S')


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


def register_ca(address=config['ui']['url'], status='idle'):
	'''Register this capture agent at the Matterhorn admin server so that it
	shows up in the admin interface.

	:param address: Address of the capture agent web ui
	:param status: Current status of the capture agent
	'''
	# If this is a backup CA we don't tell the Matterhorn core that we are here.
	# We will just run silently in the background:
	if config['agent']['backup_mode']:
		return
	params = [('address',address), ('state',status)]
	logging.info(http_request('/capture-admin/agents/%s' % \
			config['agent']['name'], params))


def recording_state(recording_id, status='upcoming'):
	'''Send the state of the current recording to the Matterhorn core.

	:param recording_id: ID of the current recording
	:param status: Status of the recording
	'''
	# If this is a backup CA we don't update the recording state. The actual CA
	# does that and we don't want to mess with it.  We will just run silently in
	# the background:
	if config['agent']['backup_mode']:
		return
	params = [('state',status)]
	logging.info(http_request('/capture-admin/recordings/%s' % \
			recording_id, params))


def get_schedule():
	'''Try to load schedule from the Matterhorn core. Returns a valid schedule
	or None on failure.
	'''
	try:
		cutoff = ''
		lookahead = config['agent']['cal_lookahead'] * 24 * 60 * 60
		if lookahead:
			cutoff = '&cutoff=%i' % ((get_timestamp() + lookahead) * 1000)
		vcal = http_request('/recordings/calendars?agentid=%s%s' % \
				(config['agent']['name'], cutoff))
	except:
		logging.error('Could not get schedule')
		logging.error(traceback.format_exc())
		return None

	cal = None
	try:
		cal = icalendar.Calendar.from_string(vcal)
	except:
		try:
			cal = icalendar.Calendar.from_ical(vcal)
		except Exception as e:
			logging.error('Could not parse ical')
			logging.error(traceback.format_exc())
			return None
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
	'''Convert datetime into a unix timestamp.

	:param dt: datetime to convert
	'''
	epoch = datetime(1970, 1, 1, 0, 0, tzinfo = dateutil.tz.tzutc())
	delta = (dt - epoch)
	return delta.days * 24 * 3600 + delta.seconds


def get_timestamp():
	'''Get current unix timestamp
	'''
	if config['agent']['ignore_timezone']:
		return unix_ts(datetime.now())
	return unix_ts(datetime.now(dateutil.tz.tzutc()))


def get_config_params(properties):
	param = []
	wdef = 'full'
	for prop in properties.split('\n'):
		if prop.startswith('org.opencastproject.workflow.config'):
			k,v = prop.split('=',1)
			k = k.split('.')[-1]
			param.append((k, v))
		elif prop.startswith('org.opencastproject.workflow.definition'):
			wdef = prop.split('=',1)[-1]
	return wdef, param


def start_capture(schedule):
	logging.info('Start recording')
	now            = get_timestamp()
	duration       = schedule[1] - now
	recording_id   = schedule[2]
	recording_name = 'recording-%i-%s' % (now, recording_id)
	recording_dir  = '%s/%s' % (config['capture']['directory'], recording_name)
	try:
		os.mkdir(config['capture']['directory'])
	except:
		pass
	os.mkdir(recording_dir)

	# Set state
	try:
		register_ca(status='capturing')
		recording_state(recording_id,'capturing')
	except:
		# Ignore it if it does not work (e.g. network issues) as it's more
		# important to get the recording as to set the correct current state in
		# the admin ui
		logging.warning('Could not set recording state before capturing')
		logging.warning(traceback.format_exc())

	tracks = []
	try:
		tracks = recording_command(recording_dir, recording_name, duration)
	except Exception as e:
		logging.error('Recording command failed')
		logging.error(traceback.format_exc())
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
			with open('%s/recording.properties' % recording_dir, 'w') as f:
				f.write(value)

	# If we are a backup CA, we don't want to actually upload anything. So let's
	# just quit here.
	if config['agent']['backup_mode']:
		return True

	# Upload everything
	try:
		register_ca(status='uploading')
		recording_state(recording_id,'uploading')
	except:
		# Ignore it if it does not work (e.g. network issues) as it's more
		# important to get the recording as to set the correct current state in
		# the admin ui
		logging.warning('Could not set recording state before capturing')
		logging.warning(traceback.format_exc())

	try:
		ingest(tracks, recording_name, recording_dir, recording_id, workflow_def,
				workflow_config)
	except:
		logging.error('Something went wrong during the upload')
		logging.error(traceback.format_exc())
		# Update state if something went wrong
		try:
			recording_state(recording_id,'upload_error')
			register_ca(status='idle')
		except:
			# Ignore it if it does not work (e.g. network issues) as it's more
			# important to get the recording as to set the correct current state
			# in the admin ui
			logging.warning('Could not set recording state')
			logging.warning(traceback.format_exc())
		return False

	# Update state
	try:
		recording_state(recording_id,'upload_finished')
		register_ca(status='idle')
	except:
		# Ignore it if it does not work (e.g. network issues) as it's more
		# important to get the recording as to set the correct current state in
		# the admin ui
		logging.warning('Could not set recording state before capturing')
		logging.warning(traceback.format_exc())
	return True


def http_request(endpoint, post_data=None):
	buf = bio()
	c = pycurl.Curl()
	url = '%s%s' % (config['server']['url'], endpoint)
	c.setopt(c.URL, url.encode('ascii', 'ignore'))
	if post_data:
		c.setopt(c.HTTPPOST, post_data)
	c.setopt(c.WRITEFUNCTION, buf.write)
	c.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
	c.setopt(pycurl.USERPWD, "%s:%s" % \
			(config['server']['username'], config['server']['password']))
	c.setopt(c.HTTPHEADER, ['X-Requested-Auth: Digest'])
	c.perform()
	status = c.getinfo(pycurl.HTTP_CODE)
	c.close()
	if status / 100 != 2:
		raise Exception('ERROR: Request to %s failed (HTTP status code %i)' % \
				(endpoint, status))
	result = buf.getvalue()
	buf.close()
	return result


def ingest(tracks, recording_name, recording_dir, recording_id, workflow_def,
		workflow_config=[]):

	# create mediapackage
	logging.info('Creating new mediapackage')
	mediapackage = http_request('/ingest/createMediaPackage')

	# add episode dc catalog
	if os.path.isfile('%s/episode.xml' % recording_dir):
		logging.info('Adding episode DC catalog')
		dc = ''
		with open('%s/episode.xml' % recording_dir, 'r') as f:
			dc = f.read()
		fields = [
				('mediaPackage', mediapackage),
				('flavor', 'dublincore/episode'),
				('dublinCore', dc)
			]
		mediapackage = http_request('/ingest/addDCCatalog', fields)

	# add series dc catalog
	if os.path.isfile('%s/series.xml' % recording_dir):
		logging.info('Adding series DC catalog')
		dc = ''
		with open('%s/series.xml' % recording_dir, 'r') as f:
			dc = f.read()
		fields = [
				('mediaPackage', mediapackage),
				('flavor', 'dublincore/series'),
				('dublinCore', dc)
			]
		mediapackage = http_request('/ingest/addDCCatalog', fields)

	# add track
	for (flavor, track) in tracks:
		logging.info('Adding track (%s)' % flavor)
		fields = [
				('mediaPackage', mediapackage), ('flavor', flavor),
				('BODY1', (pycurl.FORM_FILE, track.encode('ascii', 'ignore')))
			]
		mediapackage = http_request('/ingest/addTrack', fields)

	# ingest
	logging.info('Ingest recording')
	fields = [
			('mediaPackage', mediapackage),
			('workflowDefinitionId', workflow_def),
			('workflowInstanceId', recording_id.encode('ascii', 'ignore'))
			]
	fields += workflow_config
	mediapackage = http_request('/ingest/ingest', fields)


def safe_start_capture(schedule):
	try:
		return start_capture(schedule)
	except Exception as e:
		logging.error('Start capture failed')
		logging.error(traceback.format_exc())
		register_ca(status='idle')
		return False


def control_loop():
	last_update = 0
	schedule = []
	register = False
	while True:
		if len(schedule) and schedule[0][0] <= get_timestamp() < schedule[0][1]:
			safe_start_capture(schedule[0])
			# If something went wrong, we do not want to restart the capture
			# continuously, thus we sleep for the rest of the recording time.
			spare_time = max(0, schedule[0][1] - get_timestamp())
			if spare_time:
				logger.warning('Capture command finished but there are %i seconds'
						+ 'remaining. Sleeping...', spare_time)
				time.sleep(spare_time)
		if get_timestamp() - last_update > config['agent']['update_frequency']:
			# Make sure capture agent is registered before asking for a schedule
			if register:
				try:
					register_ca()
					register = False
				except:
					logging.error('Could not register capture agent. No connection?')
					logging.error(traceback.format_exc())
			# ry getting an updated schedult
			new_schedule = get_schedule()
			if new_schedule is None:
				# Re-register before next try if there was a connection error
				register = True
			else:
				schedule = new_schedule
			last_update = get_timestamp()
			if schedule:
				logging.info('Next scheduled recording: %s',
						datetime.fromtimestamp(schedule[0][0]))
			else:
				logging.info('No scheduled recording')
		time.sleep(1.0)


def recording_command(directory, name, duration):
	preview_dir = config['capture']['preview_dir']
	cmd = config['capture']['command']
	cmd = cmd.replace('{{time}}',       str(duration))
	cmd = cmd.replace('{{dir}}',        directory)
	cmd = cmd.replace('{{name}}',       name)
	cmd = cmd.replace('{{previewdir}}', preview_dir)
	logging.info(cmd)
	if os.system(cmd):
		raise Exception('Recording failed')

	# Remove preview files:
	for preview in config['capture']['preview']:
		try:
			os.remove(preview.replace('{{previewdir}}', preview_dir))
		except:
			logging.warning('Could not remove preview files')
			logging.warning(traceback.format_exc())

	# Return [(flavor,path),…]
	flavors = config['capture']['flavors']
	files   = config['capture']['files']
	files   = [f.replace('{{dir}}',  directory) for f in files]
	files   = [f.replace('{{name}}', name)      for f in files]
	return zip(flavors, files)


def test():
	logging.info('Starting test recording (10sec)')
	name = 'test-%i' % get_timestamp()
	logging.info('Recording name: %s', name)
	directory  = '%s/%s' % (config['capture']['directory'], name)
	logging.info('Recording directory: %s', directory)
	try:
		os.mkdir(config['capture']['directory'])
	except:
		pass
	os.mkdir(directory)
	logging.info('Created recording directory')
	logging.info('Start recording')
	recording_command(directory, name, 10)
	logging.info('Finished recording')


def run():
	try:
		register_ca()
	except:
		logging.error('Could not register capture agent. No connection?')
		logging.error(traceback.format_exc())
		exit(1)
	get_schedule()
	try:
		control_loop()
	except KeyboardInterrupt:
		pass
	register_ca(status='unknown')
