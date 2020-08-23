import logging

from traffic_monitor.models.model_monitor import Monitor
from traffic_monitor.models.feed_factory import FeedFactory

from traffic_monitor.services.observer import Subject


class MonitorFactory:
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
        return cls.singleton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('monitor_factory')

        # @staticmethod
        # def get_timezone(monitor_id: int):
        #     try:
        #         obj = Monitor.objects.get(pk=monitor_id)
        #         return obj.feed.time_zone
        #     except Monitor.DoesNotExist:
        #         return 'US/Eastern'

        # @staticmethod
        # def get_feed(monitor_name: str):
        #     return Monitor.get_feed()

        @staticmethod
        def create_feed(cam: str, time_zone: str, description: str) -> dict:
            return FeedFactory().create(cam, time_zone, description)

        @staticmethod
        def all_monitors() -> list:
            try:
                return list(Monitor.objects.all().values())
            except Exception as e:
                raise Exception(f"Failed to retrieve monitors: {e}")

        @staticmethod
        def all_feeds() -> list:
            return Monitor.all_feeds()

        @staticmethod
        def all_detectors() -> list:
            return Monitor.all_detectors()

        @staticmethod
        def create(name: str,
                   detector_name: str, detector_model: str, feed_id: str,
                   log_objects: list,
                   notification_objects: list,
                   logging_on: bool,
                   notifications_on: bool,
                   charting_on: bool) -> dict:
            """
            Create a Monitor entry which is simply a combination of detector_id and feed_cam

            :param detector_model:
            :param detector_name:
            :param notification_objects:
            :param log_objects:
            :param name: The unique name for the new Monitor
            :param feed_id: The cam id of the feed
            :param charting_on: bool(False) - If True, monitor will provide charting service
            :param notifications_on: bool(False) - If True, monitor will provide notification service
            :param logging_on: bool(True) - If True, monitor will provide logging service
            :return: The new database entry as a Django object
            """
            # If the combination already exists, just return the existing object
            try:
                _ = Monitor.objects.get(pk=name)
                raise Exception(f"Monitor with name '{name}' already exists.")
            except Monitor.DoesNotExist:
                mon = Monitor.create(name=name,
                                     detector_name=detector_name,
                                     detector_model=detector_model,
                                     feed_id=feed_id,
                                     log_objects=log_objects,
                                     notification_objects=notification_objects,
                                     logging_on=logging_on,
                                     notifications_on=notifications_on,
                                     charting_on=charting_on)
                return mon.__dict__

        @staticmethod
        def get(monitor_name) -> dict:
            """
            Retrieve a monitor object.

            :param monitor_name: The name of the monitor to retrieve
            :return: A dictionary with keys: 'success', 'message', 'monitor' here monitor is the Django monitor object.
            """
            try:
                return Monitor.objects.get(pk=monitor_name).__dict__
            except Monitor.DoesNotExist:
                raise Exception(f"Monitor with name '{monitor_name}' does not exist.")

        @staticmethod
        def toggle_logged_objects(monitor_name: str, objects: list) -> list:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.toggle_logged_objects(objects=objects)

        @staticmethod
        def toggle_notification_objects(monitor_name: str, objects: list) -> list:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.toggle_notification_objects(objects=objects)

        @staticmethod
        def set_log_objects(monitor_name: str, set_objects: list):
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.set_log_objects(set_objects=set_objects)

        @staticmethod
        def set_notification_objects(monitor_name: str, set_objects: list):
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.set_notification_objects(set_objects=set_objects)

        @staticmethod
        def get_detector_name(monitor_name: str) -> str:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.get_detector_name()

        @staticmethod
        def get_logged_objects(monitor_name: str) -> list:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.get_logged_objects()

        @staticmethod
        def get_notification_objects(monitor_name: str) -> list:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.get_notification_objects()

        @staticmethod
        def get_monitor_configuration(monitor_name: str) -> dict:
            monitor: Monitor = Monitor.get(monitor_name=monitor_name)

            return {'monitor_name': monitor.name,
                    'detector_id': monitor.detector.detector_id,
                    'detector_name': monitor.detector.name,
                    'detector_model': monitor.detector.model,
                    'feed_id': monitor.feed.cam,
                    'feed_url': monitor.feed.url,
                    'time_zone': monitor.feed.time_zone,
                    'logged_objects': monitor.log_objects,
                    'notified_objects': monitor.notification_objects,
                    'logging_on': monitor.logging_on,
                    'notifications_on': monitor.notifications_on,
                    'charting_on': monitor.charting_on}
