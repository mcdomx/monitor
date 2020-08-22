
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

    def get_logged_objects(self) -> list:
        return sorted(self.log_objects)

    def get_notification_objects(self) -> list:
        return sorted(self.notification_objects)

    def toggle_notification_object(self, object_name, trained_objects: list) -> dict:
        """
        Toggle a single object's notification status on or off by the name of the object.

        :param trained_objects:
        :param object_name: String name of the object
        :return: None if object is not supported and no action taken; else; the name of the object.
        """

        if object_name in self.notification_objects:
            self.notification_objects.remove(object_name)
            self.save()
            return {"success": True, "message": f"'{object_name}' removed from notified items."}
        elif object_name not in trained_objects:
            return {"success": False, "message": f"'{object_name}' is not a trained object."}
        else:
            self.notification_objects.append(object_name)
            self.save()
            return {"success": True, "message": f"'{object_name}' added to notified items."}

    def toggle_logged_object(self, object_name, trained_objects: list) -> dict:
        """
        Toggle a single object's logging status on or off by the name of the object.

        :param trained_objects:
        :param object_name: String name of the object
        :return: None if object is not supported and no action taken; else; the name of the object.
        """

        if object_name in self.log_objects:
            self.log_objects.remove(object_name)
            self.save()
            return {"success": True, "message": f"'{object_name}' removed from logged items."}
        elif object_name not in trained_objects:
            return {"success": False, "message": f"'{object_name}' is not a trained object."}
        else:
            self.log_objects.append(object_name)
            self.save()
            return {"success": True, "message": f"'{object_name}' added to logged items."}

    def _filter_list(self, set_objects, trained_objects) -> (list, list):
        """
        Determine items that are trained objects

        :param objects: A list that should be split between valid and invalid objects
        :return: Tuple: A list of valid objects and invalid objects
        """

        invalid_objects = set(set_objects) - set(trained_objects)
        valid_objects = set(set_objects) - set(invalid_objects)
        return list(valid_objects), list(invalid_objects)

    def set_log_objects(self, set_objects: list, trained_objects: list):
        valid_objects, invalid_objects = self._filter_list(set_objects, trained_objects)
        self.log_objects = valid_objects
        self.save()
        err_text = None
        if len(invalid_objects) > 0:
            err_text = f"The following items aren't trained and were not included: {invalid_objects}"
        return {"success": True,
                "message": f"Set logged items: {self.log_objects}. {err_text if err_text is not None else ''}"}

    def set_notification_objects(self, set_objects: list, trained_objects: list):
        valid_objects, invalid_objects = self._filter_list(set_objects, trained_objects)
        self.notification_objects = valid_objects
        self.save()
        err_text = None
        if len(invalid_objects) > 0:
            err_text = f"The following items aren't trained and were not included: {invalid_objects}"
        return {"success": True,
                "message": f"Set notification items: {self.notification_objects}. {err_text if err_text is not None else ''}"}

    def get_detector_name(self):
        return self.detector.name

    @staticmethod
    def all_feeds() -> dict:
        return FeedFactory().get_feeds()

    @staticmethod
    def all_detectors() -> dict:
        return DetectorFactory().get_detectors()

    @staticmethod
    def get_feed(feed_id):
        rv = FeedFactory().get(feed_id)
        if not rv['success']:
            return None
        return rv['feed']

    @staticmethod
    def get_detector(detector_id):
        rv = DetectorFactory().get(detector_id=detector_id)
        if not rv['success']:
            return None
        return rv['detector']

    @staticmethod
    def get_monitor(monitor_name: str):
        try:
            return Monitor.objects.get(pk=monitor_name)
        except Monitor.DoesNotExist:
            return None


