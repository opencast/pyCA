from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY

from pyca import __version__
from pyca.config import config
from pyca.db import get_session, UpstreamState


class InfoCollector(object):

    def __init__(self, db=get_session(), registry=REGISTRY):
        self.db = db
        registry.register(self)

    def collect(self):
        version = GaugeMetricFamily(
            'pyca_version',
            'Version of pyCA',
            __version__
        )
        yield version

        state = self.db.query(UpstreamState).filter(
            UpstreamState.url == config('server', 'url')).first()
        if state:
            last_sync = GaugeMetricFamily(
                'pyca_last_sync',
                'Timestamp of the last successful sync with the upstream server',
                int(state.last_synced.timestamp())
            )
            yield last_sync


INFO_COLLECTOR = InfoCollector()
