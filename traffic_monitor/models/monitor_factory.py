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

    class _Singleton(Subject):
        def __init__(self):
            Subject.__init__(self)
            self.logger = logging.getLogger('monitor_factory')
            self.subject_name = 'Monitor'

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
        def create(name: str, detector_name: str, detector_model: str, feed_id: str,
                   log_objects: list = [],
                   notification_objects: list = [],
                   logging_on: bool = True,
                   notifications_on: bool = False,
                   charting_on: bool = False) -> dict:
            """
            Create a Monitor entry which is a combination of detector and feed
            as well as the logged and notified objects.

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
                monitor: Monitor = Monitor.create(name=name,
                                                  detector_name=detector_name,
                                                  detector_model=detector_model,
                                                  feed_id=feed_id,
                                                  log_objects=log_objects,
                                                  notification_objects=notification_objects,
                                                  logging_on=logging_on,
                                                  notifications_on=notifications_on,
                                                  charting_on=charting_on)

                return monitor.__dict__

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
        def get_detector_name(monitor_name: str) -> str:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.get_detector_name()

        @staticmethod
        def get_objects(monitor_name: str, _type: str) -> list:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.get_objects(_type=_type)

        @staticmethod
        def get_value(monitor_name: str, field: str):
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return getattr(monitor, field)

        @staticmethod
        def set_objects(monitor_name: str, objects: list, _type: str) -> list:
            """
            The logged objects and notified object variables are updated with new objects.
            Changes are published to any classes that are registered with this Subject.

            :param monitor_name: Name of the monitor to update
            :param objects: The new list of objects
            :param _type: 'log' or 'notification' to reflect the type to update
            :return: The new list of objects for the respective type
            """
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            # the key is the function name of the observer to call
            # the value is the argument to that function that should be passed
            MonitorFactory().publish({'set_objects': {'objects': objects, '_type': _type}})
            return monitor.set_objects(objects, _type)

        @staticmethod
        def set_value(monitor_name: str, field: str, value):
            """
            Set the value of model objects
            :param monitor_name:
            :param field:
            :param value:
            :return:
            """
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            MonitorFactory().publish({'subject': monitor_name,
                                      'function': 'set_value',
                                      'kwargs': {field: value}})
            return monitor.set_value(field, value)

        @staticmethod
        def get_monitor_configuration(monitor_name: str) -> dict:
            monitor: Monitor = Monitor.get(monitor_name=monitor_name)

            return {'monitor_name': monitor.name,
                    'detector_id': monitor.detector.detector_id,
                    'detector_name': monitor.detector.name,
                    'detector_model': monitor.detector.model,
                    'feed_description': monitor.feed.description,
                    'feed_id': monitor.feed.cam,
                    'feed_url': monitor.feed.url,
                    'time_zone': monitor.feed.time_zone,
                    'logged_objects': monitor.log_objects,
                    'notified_objects': monitor.notification_objects,
                    'logging_on': monitor.logging_on,
                    'notifications_on': monitor.notifications_on,
                    'charting_on': monitor.charting_on}
