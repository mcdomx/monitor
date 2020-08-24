
from django.db import models
from traffic_monitor.models.detector_factory import DetectorFactory
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.feed_factory import FeedFactory
from traffic_monitor.models.model_feed import Feed


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
        rv = self.__dict__
        return f"{rv}"

    @staticmethod
    def get(monitor_name: str):
        monitor: Monitor = Monitor.objects.get(pk=monitor_name)
        FeedFactory().refresh_url(monitor.feed_id)
        return Monitor.objects.get(pk=monitor_name)

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

    def get_logged_objects(self) -> list:
        return sorted(self.log_objects)

    def get_notification_objects(self) -> list:
        return sorted(self.notification_objects)

    def toggle_notification_objects(self, objects: list) -> list:
        """
        Toggle a single object's notification status on or off by the name of the object.

        :param objects: List of named object strings
        :return: None if object is not supported and no action taken; else; the name of the object.
        """
        if len(objects) == 0:
            pass

        for o in objects:
            if o in self.notification_objects:
                self.notification_objects.remove(o)
                self.save()
            else:
                self.notification_objects.append(o)
                self.save()

        return self.notification_objects

    def toggle_logged_objects(self, objects: list) -> list:
        """
        Toggle a single object's logging status on or off by the name of the object.

        :param objects: String list of objects to toggle
        :return: None if object is not supported and no action taken; else; the name of the object.
        """

        if len(objects) == 0:
            pass

        for o in objects:
            if o in self.log_objects:
                self.log_objects.remove(o)
                self.save()
            else:
                self.log_objects.append(o)
                self.save()

        return self.log_objects

    def set_log_objects(self, set_objects: list) -> list:
        self.log_objects = set_objects
        self.save()
        return self.log_objects

    def set_notification_objects(self, set_objects: list):
        self.notification_objects = set_objects
        self.save()
        return self.notification_objects

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
