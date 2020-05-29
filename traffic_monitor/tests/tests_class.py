import logging
from django.test import TestCase

from traffic_monitor.models.model_class import Class
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.model_feed import Feed
from traffic_monitor.services.monitor_service import MonitorService

# Create your tests here.

logger = logging.getLogger('test')


class ClassTestCase(TestCase):
    def setUp(self):

        name = 'cvlib'
        m = 'yolov3'
        d_obj = Detector.objects.create(detector_id=f"{name}__{m}", name=name, model=m)
        d_obj.save()

        cam = '1EiC9bvVGnk'
        time_zone = 'US/Mountain'
        url = Feed.get_url(cam)
        f_obj = Feed.objects.create(cam=cam, url=url, description=cam, time_zone=time_zone)
        f_obj.save()

        ms = MonitorService(d_obj.detector_id, f_obj.cam)

        class_name = 'fast car'
        class_id = 'fast_car'

        obj = Class.objects.create(class_name=class_name,
                                   class_id=class_id,
                                   monitor=ms.monitor,
                                   is_monitoring=True,
                                   is_logging=True)
        obj.save()

    def test_existing_class(self):
        test_class = 'fast_car'
        try:
            c = Class.objects.filter(class_id=test_class)
            self.assertIsNotNone(c)

        except Class.DoesNotExist as e:
            logger.info(f"Class does not exist: {test_class}")
            self.assertTrue(False)

    def test_nonexisting_class(self):
        test_class = 'i_dont_exist'
        try:
            _ = Class.objects.filter(class_id=test_class)

        except Class.DoesNotExist as e:
            logger.info(f"Class does not exist: {test_class}")
            self.assertTrue(True)

