import logging
from django.test import TestCase

from traffic_monitor.models.model_monitor import Monitor, MonitorFactory
from traffic_monitor.models.model_feed import Feed
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.model_class import Class

from traffic_monitor.services.monitor_service import MonitorService, ActiveMonitors

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
        logger.info("-------------------------")
        logger.info("RUNNING CREATE MONITOR TEST")
        detector_id = 'cvlib__yolov3'
        cam = '1EiC9bvVGnk'
        try:
            ms = MonitorService(detector_id, cam)
            self.assertTrue(detector_id == ms.detector.detector_id)
            self.assertTrue(type(ms.detector) == Detector)
            self.assertTrue(cam == ms.feed.cam)

            # see that mon/log lists are the same
            self.assertTrue(set(ms.logged_objects) == set(ms.detector_class.logged_objects))
            self.assertTrue(set(ms.monitored_objects) == set(ms.detector_class.monitored_objects))

        except Exception as e:
            logger.error(e)
            self.assertTrue(False)
        logger.info("-------------------------")

    def test_run_monitor(self):
        logger.info("-------------------------")
        logger.info("RUNNING RUN MONITOR TEST")
        detector_id = 'cvlib__yolov3'
        cam = '1EiC9bvVGnk'
        try:
            ms = MonitorService(detector_id, cam)

            logger.info("Monitor service is setup.  Starting ...")
            ms.start()
            logger.info("Started!")

            # test that the monitor is stored as an active monitor
            rv = ActiveMonitors().get(ms.monitor.id)
            if rv.get('success'):
                self.assertTrue(ms == rv.get('monitor_service'))
            else:
                try:
                    _ = Monitor.objects.get(pk=ms.monitor.id)
                    db_exp_text = f"'{ms.monitor.id}' is in the database."
                except Monitor.DoesNotExist:
                    db_exp_text = f"'{ms.monitor.id}' is NOT in the database."

                raise Exception(f"Monitor with is '{ms.monitor.id}' is not active. {db_exp_text}")

            rv = ms.get_next_frame()
            logger.info("Got next frame ...")

            ms.stop()
            logger.info("Stopped Monitor Service!")

            logger.info(rv.get('frame').shape)
            self.assertTrue(rv.get('frame') is not None)
            self.assertTrue(type(rv.get('detections').get('mon')) is list)
            self.assertTrue(type(rv.get('detections').get('log')) is list)

        except Exception as e:
            logger.error(e)
            self.assertTrue(False)
        logger.info("-------------------------")

    def test_get_classes(self):
        logger.info("-------------------------")
        logger.info("RUNNING GET_CLASSES TEST")
        detector_id = 'cvlib__yolov3'
        cam = '1EiC9bvVGnk'
        try:
            ms = MonitorService(detector_id, cam)
            classes = ms.get_class_data()
            self.assertTrue(type(classes[0]) == dict)

        except Exception as e:
            logger.error(e)

        logger.info("-------------------------")
