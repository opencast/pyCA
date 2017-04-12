# -*- coding: utf-8 -*-
'''
Default configuration for pyCA.
'''

import configobj
import logging
import logging.handlers
import sys
from validate import Validator

logger = logging.getLogger(__name__)

__CFG = '''
[agent]
name             = string(default='pyca')
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
sigterm_time     = integer(min=-1, default=-1)
sigkill_time     = integer(min=-1, default=120)
exit_code        = integer(min=0, max=255, default=0)

[server]
url              = string(default='https://octestallinone.virtuos.uos.de')
username         = string(default='opencast_system_account')
password         = string(default='CHANGE_ME')
insecure         = boolean(default=False)
certificate      = string(default='')

[ui]
username         = string(default='admin')
password         = string(default='opencast')
refresh_rate     = integer(min=1, default=2)
url              = string(default='http://localhost:5000')

[logging]
syslog           = boolean(default=False)
stderr           = boolean(default=True)
level            = option('debug', 'info', 'warning', 'error', default='info')
format           = string(default='[%(name)s:%(lineno)s:%(funcName)s()] [%(levelname)s] %(message)s')
'''  # noqa

cfgspec = __CFG.split('\n')

__config = None


def update_configuration(cfgfile='/etc/pyca.conf'):
    '''Update configuration from file.

    :param cfgfile: Configuration file to load.
    '''
    configobj.DEFAULT_INTERPOLATION = 'template'
    cfg = configobj.ConfigObj(cfgfile, configspec=cfgspec)
    validator = Validator()
    val = cfg.validate(validator)
    if val is not True:
        raise ValueError('Invalid configuration: %s' % val)
    if len(cfg['capture']['files']) != len(cfg['capture']['flavors']):
        raise ValueError('List of files and flavors do not match')
    globals()['__config'] = cfg
    logger_init()
    logger.info('Configuration loaded from %s' % cfgfile)
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
        logger.info('Agent runs in bakup mode. No data will be sent to '
                    'Opencast')


def config(key=None):
    cfg = __config or update_configuration()
    return cfg[key] if key else cfg


def logger_init():
    '''Initialize logger based on configuration
    '''
    handlers = []
    logconf = config('logging')
    if logconf['syslog']:
        handlers.append(logging.handlers.SysLogHandler(address='/dev/log'))
    if logconf['stderr']:
        handlers.append(logging.StreamHandler(sys.stderr))
    for handler in handlers:
        handler.setFormatter(logging.Formatter(logconf['format']))
        logging.root.addHandler(handler)

    logging.root.setLevel(logconf['level'].upper())
    logger.info('Log level set to %s' % logconf['level'])
