# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

import getopt
import multiprocessing
import signal
import sys
from pyca import capture, config, schedule, ingest, ui, agentstate, utils
from pyca.db import get_session

USAGE = '''
Usage %s [OPTIONS] COMMAND

COMMANDS:
  run        --  Start all pyCA components except ui (default)
  capture    --  Start pyCA capture service
  ingest     --  Start pyCA ingest service
  schedule   --  Start pyCA schedule service
  agentstate --  Start pyCA agentstate service
  ui         --  Start web based user interface

OPTIONS:
  --help, -h             -- Show this help',
  --config=FILE, -c FILE -- Specify a config file',

CONFIGURATION:
  PyCA will try to find a configuration in the following order:
   - Configuration specified on the command line
   - ./etc/pyca.conf
   - /etc/pyca/pyca.conf
'''


def usage(retval=0):
    '''Print usage information to stdout and exit.
    '''
    print(USAGE % sys.argv[0])
    sys.exit(retval)


def sigint_handler(signum, frame):
    '''Intercept sigint and terminate services gracefully.
    '''
    utils.terminate(True)


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
    # Check command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hc:', ['help', 'config='])
    except getopt.GetoptError:
        usage(1)

    cfg = None
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
        if opt in ('-c', '--config'):
            cfg = arg
            break

    # Make sure we got only one command
    if len(args) > 1:
        usage(2)

    try:
        config.update_configuration(cfg)
    except ValueError as e:
        print(str(e))
        sys.exit(4)

    # Set signal handler
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)

    # Get the command with `run` as default
    cmd = (args + ['run'])[0]

    if cmd == 'run':
        # ensure database is created first
        get_session().close()
        run_all(schedule, capture, ingest, agentstate)
    elif cmd == 'schedule':
        schedule.run()
    elif cmd == 'capture':
        capture.run()
    elif cmd == 'ingest':
        ingest.run()
    elif cmd == 'agentstate':
        agentstate.run()
    elif cmd == 'ui':
        signal.signal(signal.SIGINT, signal.default_int_handler)
        ui.app.run(threaded=False)
    else:
        # Invalid command
        usage(3)


if __name__ == '__main__':
    main()
