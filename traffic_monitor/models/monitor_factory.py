import logging

from traffic_monitor.models.model_monitor import Monitor
from traffic_monitor.services.monitor_service_manager import MonitorServiceManager


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
                   notification_objects: list = None,
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
                    # detector = Detector.objects.get(pk=detector_id)
                    # feed = Feed.objects.get(pk=feed_cam)
                    return {'success': True, 'monitor': Monitor.objects.create(name=name,
                                                                               detector__id=detector_id,
                                                                               feed__cam=feed_cam,
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

            # get monitor details from db - fail if monitor doesn't exist
            rv = MonitorFactory().get(monitor_name)
            if not rv['success']:
                return {'success': False, 'message': rv['message']}

            monitor: Monitor = rv.get('monitor')
            rv = MonitorServiceManager().start(monitor_name=monitor.name,
                                               detector_id=monitor.detector.detector_id,
                                               feed_id=monitor.feed.cam,
                                               time_zone=monitor.feed.time_zone,
                                               logged_objects=monitor.log_objects,
                                               notified_objects=monitor.notification_objects,
                                               logging_on=monitor.logging_on,
                                               charting_on=monitor.charting_on,
                                               notifications_on=monitor.notifications_on)

            return rv

        @staticmethod
        def stop(monitor_name: str):
            rv = MonitorServiceManager().stop(monitor_name)
            return rv


