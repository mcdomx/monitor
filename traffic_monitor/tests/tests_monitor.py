import logging
from django.test import TestCase

from traffic_monitor.models.model_monitor import Monitor, MonitorFactory
from traffic_monitor.models.model_feed import Feed
from traffic_monitor.models.model_detector import Detector

# Create your tests here.

logger = logging.getLogger('test')


class MonitorTestCase(TestCase):
    def setUp(self):
        cam = '1EiC9bvVGnk'
        time_zone = 'US/Mountain'
        url = Feed.get_url(cam)
        f_obj = Feed.objects.create(cam=cam, url=url, description=cam, time_zone=time_zone)
        f_obj.save()

        name = 'cvlib'
        m = 'yolov3'
        d_obj = Detector.objects.create(detector_id=f"{name}__{m}", name=name, model=m)
        d_obj.save()

    def test_create_monitor(self):
        detector_id = f"cvlib__yolov3"
        cam = '1EiC9bvVGnk'
        rv = MonitorFactory().get(detector_id=detector_id, cam=cam)

        self.assertTrue(rv['success'])


    def test_run_monitor(self):
        detector_id = f"cvlib__yolov3"
        cam = '1EiC9bvVGnk'
        rv = MonitorFactory().get(detector_id=detector_id, cam=cam)