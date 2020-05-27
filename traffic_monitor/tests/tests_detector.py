import logging
from django.test import TestCase

from traffic_monitor.models.model_detector import Detector
from traffic_monitor.detectors.detector_factory import DetectorFactory

# Create your tests here.

logger = logging.getLogger('test')


class DetectorTestCase(TestCase):
    def setUp(self):
        name = 'cvlib'
        m = 'yolov3'
        obj = Detector.objects.create(detector_id=f"{name}__{m}", name=name, model=m)
        obj.save()

    def test_get_existing_detector(self):
        rv = DetectorFactory().get(detector_id='cvlib__yolov3')
        self.assertTrue(rv.get('success'))

    def test_get_nonexisting_detector(self):
        rv = DetectorFactory().get(detector_id='NN__MM')
        self.assertFalse(rv.get('success'))

    def test_create_classes(self):
        rv = DetectorFactory().get(detector_id='cvlib__yolov3')
        d = rv.get('detector')
        tr_objs = d.get_trained_objects()
        if len(tr_objs) == 0:
            logger.info("No trained objects.  Expected some.")
            self.assertTrue(False)
        else:
            logger.info(f"Found {len(tr_objs)} trained objects.")
            self.assertTrue(True)


