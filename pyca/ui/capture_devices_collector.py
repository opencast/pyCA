from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY

import glob


class CaptureDevicesCollector(object):
    '''Return metrics about available capture devices.
    '''

    def __init__(self, registry=REGISTRY):
        registry.register(self)

    def collect(self):
        devices = GaugeMetricFamily(
            'video_devices',
            'Available video devices',
            labels=['device']
        )

        device_list = glob.glob('/dev/video*')

        for device in device_list:
            devices.add_metric(
                [device],
                value=1.0
            )

        yield devices


CAPTURE_DEVICES_COLLECTOR = CaptureDevicesCollector()
