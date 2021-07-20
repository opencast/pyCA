from prometheus_client.metrics_core import StateSetMetricFamily
from prometheus_client.registry import REGISTRY

from pyca.db import ServiceStatus, Service
from pyca.utils import get_service_status


class ProcessStatusCollector(object):

    def __init__(self, registry=REGISTRY):
        registry.register(self)

    def collect(self):
        service_states = StateSetMetricFamily(
            'pyca_service_state_info',
            'Service State of pyCA processes',
            labels=['service', 'state']
        )

        service_states.add_metric(
            ['capture'],
            self.get_state_dict(ServiceStatus.str(get_service_status(Service.CAPTURE)))
        )

        service_states.add_metric(
            ['ingest'],
            self.get_state_dict(ServiceStatus.str(get_service_status(Service.INGEST)))
        )

        service_states.add_metric(
            ['schedule'],
            self.get_state_dict(ServiceStatus.str(get_service_status(Service.SCHEDULE)))
        )

        service_states.add_metric(
            ['agentstate'],
            self.get_state_dict(ServiceStatus.str(get_service_status(Service.AGENTSTATE)))
        )

        yield service_states

    @staticmethod
    def get_state_dict(state: str):
        return {
            'stopped': 'stopped' == state,
            'idle': 'idle' == state,
            'busy': 'busy' == state,
        }


PROCESS_STATUS_COLLECTOR = ProcessStatusCollector()
