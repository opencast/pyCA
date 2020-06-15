# -*- coding: utf-8 -*-
'''
    python-capture-agent
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: 2014-2017, Lars Kiesow <lkiesow@uos.de>
    :license: LGPL – see license.lgpl for more details.
'''

from pyca.utils import set_service_status, update_agent_state, timestamp
from pyca.utils import terminate
from pyca.config import config
from pyca.db import Service, ServiceStatus
import logging
import sdnotify
import time

logger = logging.getLogger(__name__)
notify = sdnotify.SystemdNotifier()


def control_loop():
    '''Main loop, updating the capture agent state.
    '''
    set_service_status(Service.AGENTSTATE, ServiceStatus.BUSY)
    notify.notify('READY=1')
    notify.notify('STATUS=Running')
    while not terminate():
        notify.notify('WATCHDOG=1')

        next_update = timestamp() + config('agent', 'update_frequency')
        while not terminate() and timestamp() < next_update:
            time.sleep(0.1)

        if not terminate():
            update_agent_state()

    logger.info('Shutting down agentstate service')
    set_service_status(Service.AGENTSTATE, ServiceStatus.STOPPED)


def run():
    '''Start the capture agent state process.
    '''
    control_loop()
