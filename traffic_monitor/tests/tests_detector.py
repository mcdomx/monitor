import logging
from django.test import TestCase
import queue
import cv2 as cv

from traffic_monitor.models.model_detector import Detector
from traffic_monitor.detectors.detector_factory import DetectorFactory
from traffic_monitor.models.model_feed import FeedFactory

# Create your tests here.

logger = logging.getLogger('test')


class DetectorTestCase(TestCase):
    def setUp(self):
        name = 'cvlib'
        m = 'yolov3'
        obj = Detector.objects.create(detector_id=f"{name}__{m}", name=name, model=m)
        obj.save()

    def test_get_existing_detector(self):
        rv = DetectorFactory().get('cvlib__yolov3', queue.Queue(1), queue.Queue(1))
        self.assertTrue(rv.get('success'))

    def test_get_nonexisting_detector(self):
        rv = DetectorFactory().get('non-existent_id', queue.Queue(1), queue.Queue(1))
        self.assertFalse(rv.get('success'))

    def test_create_classes(self):
        rv = DetectorFactory().get('cvlib__yolov3', queue.Queue(1), queue.Queue(1))
        d = rv.get('class')
        d_obj = rv.get('detector')

        tr_objs = d.get_trained_objects()
        if len(tr_objs) == 0:
            logger.info("No trained objects.  Expected some.")
            self.assertTrue(False)
        else:
            logger.info(f"Found {len(tr_objs)} trained objects.")
            self.assertTrue(True)

    def test_queues(self):
        logger.info("TESTING QUEUES AND THREADING")
        to_process_q = queue.Queue(1)
        processed_q = queue.Queue(1)
        rv = DetectorFactory().get('cvlib__yolov3', to_process_q, processed_q)
        d = rv.get('class')
        d_obj = rv.get('detector')

        # get an image
        cam_stream = '1EiC9bvVGnk'
        cam_stream_timezone = 'US/Mountain'
        rv = FeedFactory().get(cam=cam_stream, time_zone=cam_stream_timezone)
        feed = rv.get('feed')
        cap = cv.VideoCapture(feed.url)

        success = False
        frame = None
        while not success:
            success, frame = cap.read()

        # start the detector thread
        d.start()

        # put image in the q
        to_process_q.put(frame)

        logger.info("Put frame in queue ...")
        # get the processed image - wait 10 seconds max
        rv = processed_q.get(block=True, timeout=10)
        logger.info("Got processed frame ...")

        d.stop()
        logger.info("Stopped detector thread ...")

        rv_frame = rv.get('frame')
        rv_log = rv.get('log_detections')
        rv_mon = rv.get('mon_detections')

        self.assertTrue(rv_frame is not None)
        self.assertTrue(type(rv_log) == list)
        self.assertTrue(type(rv_mon) == list)




