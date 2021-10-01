from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY

from pyca.db import get_session, RecordedEvent, UpcomingEvent, Status
from pyca.utils import timestamp


class RecordingsCollector(object):

    def __init__(self, db=get_session(), registry=REGISTRY):
        self.db = db
        registry.register(self)

    def collect(self):
        '''
        Return metrics about upcoming and recorded Events
        '''
        recordings = GaugeMetricFamily(
            'pyca_events_count',
            'Count of Recorded Events with different status',
            labels=['type']
        )

        recorded_events = self.db.query(RecordedEvent)

        for status in Status.values():
            recordings.add_metric(
                [Status.str(status)],
                value=recorded_events.filter(RecordedEvent.status == status)
                                     .count()
            )

        recorded_events = self.db.query(RecordedEvent)\
                              .filter(RecordedEvent.end > timestamp())

        recorded_event_ids = [event.uid for event in recorded_events]

        upcoming_events = (self.db.query(UpcomingEvent)
                               .filter(UpcomingEvent.uid
                                       not in recorded_event_ids)
                               .count())

        recordings.add_metric(
            ['upcoming'],
            value=upcoming_events
        )

        yield recordings


RECORDINGS_COLLECTOR = RecordingsCollector()
