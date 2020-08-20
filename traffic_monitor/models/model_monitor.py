import logging

from django.db import models
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.model_feed import Feed

from traffic_monitor.detectors.detector_factory import DetectorFactory
from traffic_monitor.services.active_monitors import ActiveMonitors
from traffic_monitor.services.monitor_service import MonitorService


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

    def get_trained_objects(self) -> set:
        return DetectorFactory().get_trained_objects(self.detector.name)

    def get_logged_objects(self) -> list:
        return sorted(self.log_objects)

    def get_notification_objects(self) -> list:
        return sorted(self.notification_objects)

    def toggle_notification_object(self, object_name) -> dict:
        """
        Toggle a single object's notification status on or off by the name of the object.

        :param object_name: String name of the object
        :return: None if object is not supported and no action taken; else; the name of the object.
        """

        if object_name in self.notification_objects:
            self.notification_objects.remove(object_name)
            self.save()
            return {"success": True, "message": f"'{object_name}' removed from notified items."}
        elif object_name not in self.get_trained_objects():
            return {"success": False, "message": f"'{object_name}' is not a trained object."}
        else:
            self.notification_objects.append(object_name)
            self.save()
            return {"success": True, "message": f"'{object_name}' added to notified items."}

    def toggle_logged_object(self, object_name) -> dict:
        """
        Toggle a single object's logging status on or off by the name of the object.

        :param object_name: String name of the object
        :return: None if object is not supported and no action taken; else; the name of the object.
        """

        if object_name in self.log_objects:
            self.log_objects.remove(object_name)
            self.save()
            return {"success": True, "message": f"'{object_name}' removed from logged items."}
        elif object_name not in self.get_trained_objects():
            return {"success": False, "message": f"'{object_name}' is not a trained object."}
        else:
            self.log_objects.append(object_name)
            self.save()
            return {"success": True, "message": f"'{object_name}' added to logged items."}

    def _filter_list(self, objects) -> (list, list):
        """
        Determine items that are trained objects

        :param objects: A list that should be split between valid and invalid objects
        :return: Tuple: A list of valid objects and invalid objects
        """
        invalid_objects = set(objects) - set(self.get_trained_objects())
        valid_objects = set(objects) - set(invalid_objects)
        return list(valid_objects), list(invalid_objects)

    def set_log_objects(self, log_objects: list):
        valid_objects, invalid_objects = self._filter_list(log_objects)
        self.log_objects = valid_objects
        self.save()
        err_text = None
        if len(invalid_objects) > 0:
            err_text = f"The following items aren't trained and were not included: {invalid_objects}"
        return {"success": True, "message": f"Set logged items: {self.log_objects}. {err_text if err_text is not None else ''}"}

    def set_notification_objects(self, notification_objects: list):
        valid_objects, invalid_objects = self._filter_list(notification_objects)
        self.log_objects = valid_objects
        self.save()
        err_text = None
        if len(invalid_objects) > 0:
            err_text = f"The following items aren't trained and were not included: {invalid_objects}"
        return {"success": True,
                "message": f"Set notification items: {self.log_objects}. {err_text if err_text is not None else ''}"}


class MonitorFactory:
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
        return cls.singleton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('monitor_factory')

        @staticmethod
        def get_timezone(monitor_id: int):
            try:
                obj = Monitor.objects.get(pk=monitor_id)
                return obj.feed.time_zone
            except Monitor.DoesNotExist:
                return 'US/Eastern'

        @staticmethod
        def getall() -> dict:
            try:
                mon_objs = Monitor.objects.all()
                return {'success': True, 'monitors': mon_objs}
            except Exception as e:
                return {'success': False, 'message': f"Failed to retrieve detectors"}

        @staticmethod
        def create(name: str, detector_id: str, feed_cam: str,
                   log_objects: list = None,
                   notification_objects: list = None ,
                   logging_on: bool = True,
                   notifications_on: bool = False,
                   charting_on: bool = False) -> dict:
            """
            Create a Monitor entry which is simply a combination of detector_id and feed_cam

            :param notification_objects:
            :param log_objects:
            :param name: The unique name for the new Monitor
            :param detector_id: The id of the detector
            :param feed_cam: The cam id of the feed
            :param charting_on: bool(False) - If True, monitor will provide charting service
            :param notifications_on: bool(False) - If True, monitor will provide notification service
            :param logging_on: bool(True) - If True, monitor will provide logging service
            :return: The new database entry as a Django object
            """
            # If the combination already exists, just return the existing object
            try:
                obj = Monitor.objects.get(name=name)
                return {'success': False, 'message': f"Monitor with name '{name}' already exists.", 'monitor': obj}
            except Monitor.DoesNotExist:
                try:
                    detector = Detector.objects.get(pk=detector_id)
                    feed = Feed.objects.get(pk=feed_cam)
                    return {'success': True, 'monitor': Monitor.objects.create(name=name,
                                                                               detector=detector,
                                                                               feed=feed,
                                                                               log_objects=log_objects,
                                                                               notification_objects=notification_objects,
                                                                               logging_on=logging_on,
                                                                               notifications_on=notifications_on,
                                                                               charting_on=charting_on),
                            'message': "New monitor created."}
                except Detector.DoesNotExist:
                    return {'success': False, 'message': f"detector_id '{detector_id}' does not exist."}
                except Feed.DoesNotExist:
                    return {'success': False, 'message': f"feed_cam '{feed_cam}' does not exist."}

        @staticmethod
        def get(monitor_name) -> dict:
            """
            Returns Monitor object.  If the monitor doesn't already exist,
            it is created if a stream and detector exist.

            For extensibility:
                Update this function to add new detection models.
                New models will require new class that inherits from Detector class.

            :param monitor_name: The name of the monitor to retrieve
            :return: A dictionary with keys: 'success', 'message', 'monitor' here monitor is the Django monitor object.
            """

            try:
                mon_obj = Monitor.objects.get(pk=monitor_name)
                return {'success': True, 'monitor': mon_obj, 'message': "Monitor successfully retrieved."}
            except Monitor.DoesNotExist:
                return {'success': False, 'monitor': None,
                        'message': f"Monitor with name '{monitor_name}' does not exist."}

        @staticmethod
        def start(monitor_name: str):
            """
            Setup and start a monitoring service with respective support services for logging, notifying and charting.

            :param monitor_name: Name of monitor to start
            :return: Dictionary with 'success' bool and 'message' indicating result
            """

            # no need to start monitor if it is already running
            if ActiveMonitors().is_active(monitor_name):
                return {'success': False, 'message': f"Monitor {monitor_name} is already active."}

            # get monitor details from db - fail if monitor doesn't exist
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return {'success': False, 'message': rv['message']}

            monitor = rv.get('monitor')
            ms = MonitorService(monitor=monitor)
            rv = ActiveMonitors().add(monitor_name=monitor_name, monitor_service=ms)
            if rv['success']:
                rv = ms.start()

            return rv

