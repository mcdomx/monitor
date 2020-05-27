import logging
from django.test import TestCase

from traffic_monitor.models.model_monitor import Monitor, MonitorFactory
from traffic_monitor.models.model_feed import Feed
from traffic_monitor.models.model_detector import Detector

from traffic_monitor.services.monitor_service import MonitorService

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
        logger.info("RUNNING CREATE MONITOR TEST")
        detector_id = 'cvlib__yolov3'
        cam = '1EiC9bvVGnk'
        try:
            ms = MonitorService(detector_id, cam)
            self.assertTrue(detector_id == ms.detector.detector_id)
            self.assertTrue(type(ms.detector) == Detector)
            self.assertTrue(cam == ms.feed.cam)
        except Exception as e:
            logger.error(e)
            self.assertTrue(False)

    def test_run_monitor(self):
        logger.info("RUNNING RUN MONITOR TEST")
        detector_id = 'cvlib__yolov3'
        cam = '1EiC9bvVGnk'
        try:
            ms = MonitorService(detector_id, cam)

            logger.info("Monitor service is setup.  Starting ...")
            ms.start()
            logger.info("Started!")
            rv = ms.get_next_frame()
            logger.info("Got next frame ...")
            ms.stop()
            logger.info("Stopped Monitor Service!")

            logger.info(rv.get('frame').shape)
            self.assertTrue(rv.get('frame') is not None)
            self.assertTrue(type(rv.get('mon_detections')) is list)
            self.assertTrue(type(rv.get('log_detections')) is list)

        except Exception as e:
            logger.error(e)
            self.assertTrue(False)
