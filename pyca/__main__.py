#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2016, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

import sys
import getopt
import os
import multiprocessing
from pyca import capture, config, schedule

USAGE = '''
Usage %s [OPTIONS] COMMAND

COMMANDS:
  run  --  Start pyCA as capture agent (default)
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


def main():

    cfg = '/etc/pyca.conf'
    if not os.path.isfile(cfg):
        cfg = './etc/pyca.conf'

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
        config.update_configuration(cfg)
        p_schedule = multiprocessing.Process(target=schedule.run)
        p_capture = multiprocessing.Process(target=capture.run)
        p_schedule.start()
        p_capture.start()
        try:
            p_schedule.join()
            p_capture.join()
        except KeyboardInterrupt:
            pass
    elif cmd == 'ui':
        import pyca.ui
        pyca.ui.app.run(host='0.0.0.0')
    else:
        # Invalid command
        usage(3)


if __name__ == '__main__':
    main()
