
import logging
from django.db import models
from traffic_monitor.models.detector_factory import DetectorFactory
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.feed_factory import FeedFactory
from traffic_monitor.models.model_feed import Feed


logger = logging.getLogger('monitor')


class Monitor(models.Model):
    """
    A Monitor is a combination of video feed and detector.
    Since Monitors are built during run-time, a MonitorFactory should be used to
    create and retrieve Monitor objects.
    """
    name = models.CharField(primary_key=True, max_length=64)
    detector = models.ForeignKey(Detector, on_delete=models.CASCADE, related_name='detector_log', null=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='feed_log', null=True)
    log_objects = models.JSONField(default=list)
    notification_objects = models.JSONField(default=list)
    logging_on = models.BooleanField(default=True)
    notifications_on = models.BooleanField(default=False)
    charting_on = models.BooleanField(default=False)

    def __str__(self):
        # this is set to self.name so that the admin page shows the monitor name
        return self.name
        # rv = self.__dict__
        # return f"{rv}"

    @staticmethod
    def get(monitor_name: str):
        try:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            FeedFactory().refresh_url(monitor.feed_id)
            return Monitor.objects.get(pk=monitor_name)
        except Monitor.DoesNotExist as e:
            logger.error(f"Monitor Does not Exist: {monitor_name} {e}")

    @staticmethod
    def create(**kwargs):
        detector = Detector.objects.get(name=kwargs.get('detector_name'), model=kwargs.get('detector_model'))
        feed = Feed.objects.get(pk=kwargs.get('feed_id'))
        kwargs.pop('detector_name')
        kwargs.pop('detector_model')
        kwargs.pop('feed_id')
        kwargs.update({'detector': detector})
        kwargs.update({'feed': feed})
        return Monitor.objects.create(**kwargs)

    def get_objects(self, _type: str) -> list:
        if _type == 'log':
            return sorted(self.log_objects)
        elif _type == 'notification':
            return sorted(self.notification_objects)
        else:
            raise Exception(f"Object type '{_type}' not supported.")

    def set_objects(self, objects: list, _type: str) -> list:
        if _type == 'log':
            self.log_objects = objects
            self.save()
            return sorted(self.log_objects)
        elif _type == 'notification':
            self.notification_objects = objects
            self.save()
            return sorted(self.notification_objects)
        else:
            raise Exception(f"Object type '{_type}' not supported.")

    def set_value(self, field: str, value):
        setattr(self, field, value)
        self.save(update_fields={field})
        return getattr(self, field)

    def get_detector_name(self):
        return self.detector.name

    @staticmethod
    def all_feeds() -> list:
        return FeedFactory().get_feeds()

    @staticmethod
    def all_detectors() -> list:
        return DetectorFactory().get_detectors()

    @staticmethod
    def get_feed(feed_id):
        return FeedFactory().get(feed_id)

    @staticmethod
    def get_detector(detector_id) -> dict:
        return DetectorFactory().get(detector_id=detector_id)

    @staticmethod
    def get_monitor(monitor_name: str) -> dict:
        return Monitor.objects.get(pk=monitor_name)
