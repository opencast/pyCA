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

        for service in Service.values():
            service_states.add_metric(
                [Service.str(service)],
                self.get_state_dict(get_service_status(service))
            )

        yield service_states

    @staticmethod
    def get_state_dict(state: str):
        return {ServiceStatus.str(s): s == state
                for s in ServiceStatus.values()}


PROCESS_STATUS_COLLECTOR = ProcessStatusCollector()
