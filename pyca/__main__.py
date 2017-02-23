# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

import getopt
import multiprocessing
import os
import signal
import sys
from pyca import capture, config, schedule, ingest

USAGE = '''
Usage %s [OPTIONS] COMMAND

COMMANDS:
  run      --  Start all pyCA components except ui (default)
  capture  --  Start pyCA capture service
  ingest   --  Start pyCA ingest service
  schedule --  Start pyCA schedule service
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


def sigint_handler(signum, frame):
    '''Intercept sigint and terminate services gracefully.
    '''
    for mod in (capture, ingest, schedule):
        mod.terminate = True


def sigterm_handler(signum, frame):
    '''Intercept sigterm and terminate all processes.
    '''
    sigint_handler(signum, frame)
    for process in multiprocessing.active_children():
        process.terminate()
    sys.exit(0)


def run_all(*modules):
    '''Start all services.
    '''
    processes = [multiprocessing.Process(target=mod.run) for mod in modules]
    for p in processes:
        p.start()
    for p in processes:
        p.join()


def main():
    # Set signal handler
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)

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
        run_all(schedule, capture, ingest)
    elif cmd == 'schedule':
        schedule.run()
    elif cmd == 'capture':
        capture.run()
    elif cmd == 'ingest':
        ingest.run()
    elif cmd == 'ui':
        import pyca.ui
        pyca.ui.app.run(host='0.0.0.0')
    else:
        # Invalid command
        usage(3)


if __name__ == '__main__':
    main()
