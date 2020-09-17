
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
    detector_sleep_throttle = models.IntegerField(default=5)
    detector_confidence = models.FloatField(default=.50)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='feed_log', null=True)
    log_objects = models.JSONField(default=list)
    notification_objects = models.JSONField(default=list)
    logging_on = models.BooleanField(default=True)
    log_interval = models.IntegerField(default=60)
    notifications_on = models.BooleanField(default=False)
    charting_on = models.BooleanField(default=False)
    charting_time_horizon = models.CharField(default='6', max_length=8)
    charting_objects = models.JSONField(default=list)
    charting_time_zone = models.CharField(max_length=32)
    class_colors = models.JSONField(default=dict)


    def __str__(self):
        # this is set to self.name so that the admin page shows the monitor name
        return self.name
        # rv = self.__dict__
        # return f"{rv}"

    def refresh_url(self):
        # monitor: Monitor = Monitor.objects.get(pk=monitor_name)
        FeedFactory().refresh_url(self.feed_id)
        return self

    @staticmethod
    def get(monitor_name: str):
        try:
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

    @staticmethod
    def update_monitor(kwargs):

        monitor_name = kwargs.get('monitor_name')
        kwargs.pop('monitor_name')

        if 'detector_name' in kwargs.keys() or 'detector_model' in kwargs.keys():
            detector_name = kwargs.get('detector_name', Monitor.objects.get(pk=monitor_name).detector.name)
            detector_model = kwargs.get('detector_model', Monitor.objects.get(pk=monitor_name).detector.model)
            detector = Detector.objects.get(name=detector_name, model=detector_model)
            if 'detector_name' in kwargs.keys():
                kwargs.pop('detector_name')
            if 'detector_model' in kwargs.keys():
                kwargs.pop('detector_model')
            kwargs.update({'detector': detector})

        if Monitor.objects.filter(name=monitor_name).update(**kwargs):
            return Monitor.objects.get(name=monitor_name)
        else:
            raise Exception(f"Unable to save monitor update: {monitor_name}")

    def get_objects(self, _type: str) -> list:
        if _type == 'log':
            return sorted(self.log_objects)
        elif _type == 'all_log':
            rs = self.monitor_log.values_list('class_name').distinct()
            return sorted([r[0] for r in rs])
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
