#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
    python-matterhorn-ca
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2015, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

import sys
import getopt
import os
from pyca import ca

USAGE = '''
Usage %s [OPTIONS] COMMAND

COMMANDS:
  run  --  Start pyCA as capture agent (default)
  test --  Test recording command
  ui   --  Start web based user interface

OPTIONS:
  --help, -h             -- Show this help',
  --config=FILE, -c FILE -- Specify a config file',

CONFIGURATION:
  PyCA will try to find a configuration in the following order:
   - Configuration specified on the command line
   - /etc/pyca.conf
   - ./etc/pyca.conf
'''

def usage(retval=0):
    '''Print usage information to stdout and exit.
    '''
    print(USAGE % sys.argv[0])
    sys.exit(retval)


if __name__ == '__main__':

    cfg = '/etc/pyca.conf' if os.path.isfile('/etc/pyca.conf') else './etc/pyca.conf'

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hc:', ['help', 'config='])

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
            if opt in ('-c', '--config'):
                cfg = arg
                break
    except (getopt.GetoptError, ValueError):
        usage(1)

    # Make sure we got only one command
    if len(args) > 1:
        usage(2)

    cmd = (args + ['run'])[0]

    if cmd == 'run':
        ca.update_configuration(cfg)
        ca.run()
    elif cmd == 'test':
        ca.update_configuration(cfg)
        ca.test()
    elif cmd == 'ui':
        import pyca.ui
        pyca.ui.app.run(host='0.0.0.0')
    else:
        # Invalid command
        usage(3)
