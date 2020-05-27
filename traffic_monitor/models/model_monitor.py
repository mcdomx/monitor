
import logging

from django.db import models
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.model_feed import Feed


class Monitor(models.Model):
    # use Django auto PrimaryKey of 'id'
    detector = models.ForeignKey(Detector, on_delete=models.CASCADE, related_name='detector_log', null=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='feed_log', null=True)


class MonitorFactory:
    singelton = None

    def __new__(cls):
        if cls.singelton is None:
            cls.singelton = cls._Singleton()
        return cls.singelton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('monitor_factory')
            self.monitors = {}

        def get(self, detector_id, cam) -> dict:
            """
            Returns Monitor object.
            Update this function to add new detection models.
            New models will require new class that inherits from Detector class.
            """

            # See if an existing monitor exists
            mon_obj = None
            try:
                mon_obj = Monitor.objects.get(detector__detector_id=detector_id, feed__cam=cam)
                return {'success': True, 'monitor': mon_obj}
            except Monitor.DoesNotExist as e:
                # get the Detector
                try:
                    detector = Detector.objects.get(pk=detector_id)
                    feed = Feed.objects.get(pk=cam)
                    mon_obj = Monitor.objects.create(detector=detector, feed=feed)
                    return {'success': True, 'monitor': mon_obj}
                except Detector.DoesNotExist as e:
                    self.logger.info(f"Detector ID not in DB: {detector_id}")
                    return {'success': False, 'message': f"Detector ID not in DB: {detector_id}"}
                except Feed.DoesNotExist as e:
                    self.logger.info(f"Feed does not exist: {cam}")
                    return {'success': False, 'message': f"Feed does not exist: {cam}"}
