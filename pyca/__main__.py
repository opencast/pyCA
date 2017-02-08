#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
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
  run      --  Start all pyCA components except ui (default)
  capture  --  Start pyCA capturer
  schedule --  Start pyCA scheduler
  ui       --  Start web based user interface

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


def start_all(processes):
    '''Start all processes which are not alive.
    '''
    for p in processes:
        if not p.is_alive():
            p.start()


def main():

    # Probe for configuration file location
    cfg = '/etc/pyca.conf'
    if not os.path.isfile(cfg):
        cfg = './etc/pyca.conf'

    # Check command line options
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

    # Get the command with `run` as default
    cmd = (args + ['run'])[0]

    config.update_configuration(cfg)
    if cmd == 'run':
        processes = [multiprocessing.Process(target=schedule.run),
                     multiprocessing.Process(target=capture.run)]
        start_all(processes)
        try:
            # Ensure processes are restarted until all are dead
            while [p for p in processes if p.is_alive()]:
                start_all(processes)
                for p in processes:
                    p.join(2)
        except KeyboardInterrupt:
            pass
    elif cmd == 'schedule':
        schedule.run()
    elif cmd == 'capture':
        capture.run()
    elif cmd == 'ui':
        import pyca.ui
        pyca.ui.app.run(host='0.0.0.0')
    else:
        # Invalid command
        usage(3)


if __name__ == '__main__':
    main()
