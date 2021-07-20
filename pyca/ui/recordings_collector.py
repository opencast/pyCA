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
        recordings = GaugeMetricFamily('pyca_events_count',
                                       'Count of Recorded Events with different status',
                                       labels=['type'])
        recordings.add_metric(
            ['upcoming'],
            value=self.db.query(UpcomingEvent).filter(UpcomingEvent.start >= timestamp()).count()
        )
        recordings.add_metric(
            ['recording'],
            value=self.db.query(RecordedEvent).filter(RecordedEvent.status == Status.RECORDING).count()
        )

        recorded_events = self.db.query(RecordedEvent)

        # Filter RecordedEvents for different Status
        recordings.add_metric(
            ['failed_recording'],
            value=recorded_events.filter(RecordedEvent.status == Status.FAILED_RECORDING).count()
        )

        recordings.add_metric(
            ['finished_recording'],
            value=recorded_events.filter(RecordedEvent.status == Status.FINISHED_RECORDING).count()
        )

        recordings.add_metric(
            ['uploading'],
            value=recorded_events.filter(RecordedEvent.status == Status.UPLOADING).count()
        )

        recordings.add_metric(
            ['failed_uploading'],
            value=recorded_events.filter(RecordedEvent.status == Status.FAILED_UPLOADING).count()
        )

        recordings.add_metric(
            ['finished_uploading'],
            value=recorded_events.filter(RecordedEvent.status == Status.FINISHED_UPLOADING).count()
        )

        recordings.add_metric(
            ['partial_recording'],
            value=recorded_events.filter(RecordedEvent.status == Status.PARTIAL_RECORDING).count()
        )

        recordings.add_metric(
            ['paused_after_recordings'],
            value=recorded_events.filter(RecordedEvent.status == Status.PAUSED_AFTER_RECORDING).count()
        )

        yield recordings


RECORDINGS_COLLECTOR = RecordingsCollector()
