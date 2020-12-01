# -*- coding: utf-8 -*-
'''
Default configuration for pyCA.
'''

import configobj
import logging
import logging.handlers
import os
import socket
import sys
from validate import Validator

logger = logging.getLogger(__name__)

__CFG = '''
[agent]
name             = string(default='')
update_frequency = integer(min=5, default=60)
cal_lookahead    = integer(min=0, default=14)
backup_mode      = boolean(default=false)
database         = string(default='sqlite:///pyca.db')

[capture]
directory        = string(default='./recordings')
command          = string(default='ffmpeg -nostats -re -f lavfi -r 25 -i testsrc -t {{time}} {{dir}}/{{name}}.webm')
flavors          = force_list(default=list('presenter/source'))
files            = force_list(default=list('{{dir}}/{{name}}.webm'))
preview_dir      = string(default='./recordings')
preview          = force_list(default=list())
sigcustom        = integer(min=1, default=2)
sigcustom_time   = integer(min=-1, default=-1)
sigterm_time     = integer(min=-1, default=-1)
sigkill_time     = integer(min=-1, default=120)
exit_code        = integer(min=0, max=255, default=0)

[ingest]
delay_max        = integer(min=0, default=0)
delay_min        = integer(min=0, default=0)
delete_after_upload = boolean(default=false)
upload_catalogs  = boolean(default=false)
upload_rate      = string(default='0')

[server]
url              = string(default='https://develop.opencast.org')
auth_method      = option('basic', 'digest', default='digest')
username         = string(default='opencast_system_account')
password         = string(default='CHANGE_ME')
insecure         = boolean(default=False)
certificate      = string(default='')

[ui]
username         = string(default='admin')
password         = string(default='opencast')
refresh_rate     = integer(min=1, default=10)
url              = string(default='http://localhost:5000')
log_command      = string(default='')

[logging]
syslog           = boolean(default=False)
stderr           = boolean(default=True)
file             = string(default='')
level            = option('debug', 'info', 'warning', 'error', default='info')
format           = string(default='[%(name)s:%(lineno)s:%(funcName)s()] [%(levelname)s] %(message)s')

[services]
'''  # noqa

cfgspec = __CFG.split('\n')

__config = None


def configuration_file(cfgfile):
    '''Find the best match for the configuration file.
    '''
    if cfgfile is not None:
        return cfgfile
    # If no file is explicitely specified, probe for the configuration file
    # location.
    cfg = './etc/pyca.conf'
    if not os.path.isfile(cfg):
        return '/etc/pyca/pyca.conf'
    return cfg


def update_configuration(cfgfile=None):
    '''Update configuration from file.

    :param cfgfile: Configuration file to load.
    '''
    configobj.DEFAULT_INTERPOLATION = 'template'
    cfgfile = configuration_file(cfgfile)
    cfg = configobj.ConfigObj(cfgfile, configspec=cfgspec, encoding='utf-8')
    validator = Validator()
    val = cfg.validate(validator)
    if val is not True:
        raise ValueError('Invalid configuration: %s' % val)
    if len(cfg['capture']['files']) != len(cfg['capture']['flavors']):
        raise ValueError('List of files and flavors do not match')
    if not cfg['agent']['name']:
        cfg['agent']['name'] = 'pyca@' + socket.gethostname()
    globals()['__config'] = cfg
    logger_init()
    if cfg['server'].get('url', '').endswith('/'):
        logger.warning('Base URL ends with /. This is most likely a '
                       'configuration error. The URL should contain nothing '
                       'of the service paths.')
    if cfg['ingest'].get('upload_rate'):
        # Limit upload rate in bytes per second
        upload_rate = cfg['ingest'].get('upload_rate').lower()
        if upload_rate.endswith('m'):
            upload_rate = upload_rate[0:-1] + '000000'
        elif upload_rate.endswith('k'):
            upload_rate = upload_rate[0:-1] + '000'
        cfg['ingest']['upload_rate'] = int(upload_rate)
    logger.info('Configuration loaded from %s', cfgfile)
    check()
    return cfg


def check():
    '''Check configuration for sanity.
    '''
    if config('server')['insecure']:
        logger.warning('HTTPS CHECKS ARE TURNED OFF. A SECURE CONNECTION IS '
                       'NOT GUARANTEED')
    if config('server')['certificate']:
        # Ensure certificate exists and is readable
        open(config('server')['certificate'], 'rb').close()
    if config('agent')['backup_mode']:
        logger.info('Agent runs in backup mode. No data will be sent to '
                    'Opencast')


def config(*args):
    '''Get a specific configuration value or the whole configuration, loading
    the configuration file if it was not before.

    :param key: optional configuration key to return
    :type key: string
    :return: Part of the configuration object containing the configuration
             or configuration value.
             If a part of the configuration object (e.g. configobj.Section) is
             returned, it can be treated like a dictionary.
             Returning None, if the configuration value is not found.
    '''
    cfg = __config or update_configuration()
    for key in args:
        if cfg is None:
            return
        cfg = cfg.get(key)
    return cfg


def logger_init():
    '''Initialize logger based on configuration
    '''
    handlers = []
    logconf = config('logging')
    if logconf['syslog']:
        handlers.append(logging.handlers.SysLogHandler(address='/dev/log'))
    if logconf['stderr']:
        handlers.append(logging.StreamHandler(sys.stderr))
    if logconf['file']:
        handlers.append(logging.handlers.WatchedFileHandler(logconf['file']))
    for handler in handlers:
        handler.setFormatter(logging.Formatter(logconf['format']))
        logging.root.addHandler(handler)

    logging.root.setLevel(logconf['level'].upper())
    logger.info('Log level set to %s', logconf['level'])
