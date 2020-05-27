import logging
from django.test import TestCase

from traffic_monitor.models.model_class import Class

# Create your tests here.

logger = logging.getLogger('test')


class ClassTestCase(TestCase):
    def setUp(self):

        class_name = 'fast car'
        class_id = 'fast_car'
        detector_id = 'det_123'
        monitor = True
        log = True

        obj = Class.objects.create(key=f"{detector_id}__{class_id}",
                                   class_name=class_name,
                                   class_id=class_id,
                                   detector_id=detector_id,
                                   monitor=monitor,
                                   log=log)
        obj.save()

    def test_existing_class(self):
        test_class = 'det_123__fast_car'
        try:
            c = Class.objects.get(pk=test_class)
            self.assertIsNotNone(c)

        except Class.DoesNotExist as e:
            logger.info(f"Class does not exist: {test_class}")
            self.assertTrue(False)

    def test_nonexisting_class(self):
        test_class = 'det_123__fast_car'
        try:
            c = Class.objects.get(pk=test_class)
            self.assertIsNotNone(c)

        except Class.DoesNotExist as e:
            logger.info(f"Class does not exist: {test_class}")
            self.assertTrue(False)

