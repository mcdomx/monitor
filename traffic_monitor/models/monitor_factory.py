import logging

from traffic_monitor.models.model_monitor import Monitor
from traffic_monitor.services.monitor_service import MonitorService


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
        #     Monitor.get_feed()

        @staticmethod
        def all_monitors() -> dict:
            try:
                mon_objs = Monitor.objects.all()
                return {'success': True, 'monitors': mon_objs}
            except Exception as e:
                return {'success': False, 'message': f"Failed to retrieve detectors"}

        @staticmethod
        def all_feeds() -> dict:
            return Monitor.all_feeds()

        @staticmethod
        def all_detectors() -> dict:
            return Monitor.all_detectors()

        @staticmethod
        def create(name: str, detector_id: str, feed_cam: str,
                   log_objects: list,
                   notification_objects: list,
                   logging_on: bool,
                   notifications_on: bool,
                   charting_on: bool) -> dict:
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
                    detector = Monitor.get_detector(detector_id)
                    feed = Monitor.get_feed(feed_cam)
                    return {'success': True, 'monitor': Monitor.objects.create(name=name,
                                                                               detector=detector,
                                                                               feed=feed,
                                                                               log_objects=log_objects,
                                                                               notification_objects=notification_objects,
                                                                               logging_on=logging_on,
                                                                               notifications_on=notifications_on,
                                                                               charting_on=charting_on),
                            'message': "New monitor created."}
                # except Detector.DoesNotExist:
                #     return {'success': False, 'message': f"detector_id '{detector_id}' does not exist."}
                # except Feed.DoesNotExist:
                #     return {'success': False, 'message': f"feed_cam '{feed_cam}' does not exist."}
                except Exception as e:
                    return {'success': False, 'message': f"{e}"}

        @staticmethod
        def get(monitor_name) -> dict:
            """
            Retrieve a monitor object.

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
        def toggle_logged_object(monitor_name: str, object_name: str, trained_objects: list) -> dict:
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return rv

            monitor: Monitor = rv['monitor']

            return monitor.toggle_logged_object(object_name=object_name, trained_objects=trained_objects)

        @staticmethod
        def toggle_notification_object(monitor_name: str, object_name: str, trained_objects: list) -> dict:
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return rv

            monitor: Monitor = rv['monitor']

            return monitor.toggle_notification_object(object_name=object_name, trained_objects=trained_objects)

        @staticmethod
        def set_log_objects(monitor_name: str, set_objects: list, trained_objects: list):
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return rv

            monitor: Monitor = rv['monitor']

            return monitor.set_log_objects(set_objects=set_objects, trained_objects=trained_objects)

        @staticmethod
        def set_notification_objects(monitor_name: str, set_objects: list, trained_objects: list):
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return rv

            monitor: Monitor = rv['monitor']

            return monitor.set_notification_objects(set_objects=set_objects, trained_objects=trained_objects)

        @staticmethod
        def get_detector_name(monitor_name: str):
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return rv

            monitor: Monitor = rv['monitor']

            return {'success': True, 'name': monitor.get_detector_name()}

        @staticmethod
        def get_logged_objects(monitor_name: str):
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return rv

            monitor: Monitor = rv['monitor']

            return {'success': True, 'objects': monitor.get_logged_objects()}

        @staticmethod
        def get_notification_objects(monitor_name: str) -> dict:
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return rv

            monitor: Monitor = rv['monitor']

            return {'success': True, 'objects': monitor.get_notification_objects()}

        @staticmethod
        def get_monitor_configuration(monitor_name: str) -> dict:
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return rv

            monitor: Monitor = rv['monitor']

            return {'success': True,
                    'configuration': {'monitor_name': monitor.name,
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
                                      'charting_on': monitor.charting_on}}
