# -*- coding: utf-8 -*-
'''
Default configuration for pyCA.
'''

import logging
from configobj import ConfigObj
from validate import Validator

logger = logging.getLogger(__name__)

__CFG = '''
[agent]
name             = string(default='pyca')
ignore_timezone  = boolean(default=False)
update_frequency = integer(min=5, default=60)
cal_lookahead    = integer(min=0, default=14)
backup_mode      = boolean(default=false)
database         = string(default='sqlite:///pyca.db')

[capture]
directory        = string(default='./recordings')
command          = string(default='ffmpeg -nostats -re -f lavfi -r 25 -i testsrc -t {{time}} {{dir}}/{{name}}.mp4')
flavors          = force_list(default=list('presenter/source'))
files            = force_list(default=list('{{dir}}/{{name}}.mp4'))
preview_dir      = string(default='./recordings')
preview          = force_list(default=list())

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
'''  # noqa

cfgspec = __CFG.split('\n')

__config = None


def update_configuration(cfgfile='/etc/pyca.conf'):
    '''Update configuration from file.

    :param cfgfile: Configuration file to load.
    '''
    cfg = ConfigObj(cfgfile, configspec=cfgspec)
    validator = Validator()
    cfg.validate(validator)
    globals()['__config'] = cfg
    check()
    return cfg


def check():
    '''Check configuration for sanity.
    '''
    if config()['server']['insecure']:
        logger.warning('INSECURE: HTTPS CHECKS ARE TURNED OFF. A SECURE '
                        'CONNECTION IS NOT GUARANTEED')
    if config()['server']['certificate']:
        try:
            with open(config()['server']['certificate'], 'rb'):
                pass
        except IOError as err:
            logger.warning('Could not read certificate file: %s', err)


def config(key=None):
    return __config or update_configuration()
