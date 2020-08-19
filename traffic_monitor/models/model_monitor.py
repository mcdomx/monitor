
import logging

from django.db import models
from traffic_monitor.models.model_detector import Detector
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

    # @staticmethod
    # def get(monitor_id: int):
    #     try:
    #         rv = Monitor.objects.get(pk=monitor_id)
    #         return {'success': True, 'monitor': rv}
    #     except Monitor.DoesNotExist:
    #         return {'success': False, 'message': f"Monitor with id {monitor_id} does not exist."}

    def __str__(self):
        rv = self.__dict__
        try:
            del rv['_state']
        except KeyError:
            pass
        return f"{rv}"


class MonitorFactory:
    singelton = None

    def __new__(cls):
        if cls.singelton is None:
            cls.singelton = cls._Singleton()
        return cls.singelton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('monitor_factory')

        # @staticmethod
        # def add(detector_id: str, feed_cam: str, name: str = None) -> dict:
        #
        #     # See if a monitor with name already exists - fail if it does
        #     try:
        #         Monitor.objects.get(pk=name)
        #         return {'success': False,
        #                 'message': f"Monitor '{name}' already exists. Use a unique name for the Monitor."}
        #     except Monitor.DoesNotExist:
        #         pass
        #
        #     # try to add monitor - fail if detector or feed do not already exist
        #     try:
        #         det_obj = Detector.objects.get(pk=detector_id)
        #         feed_obj = Feed.objects.get(pk=feed_cam)
        #         return {'success': True, 'monitor': Monitor.objects.create(name=name, detector=det_obj, feed=feed_obj)}
        #     except Detector.DoesNotExist:
        #         return {'success': False, 'message': f"Detector '{detector_id}' does not exist."}
        #     except Feed.DoesNotExist:
        #         return {'success': False, 'message': f"Feed '{feed_cam}' does not exist."}

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
        def create(name: str, detector_id: str, feed_cam: str) -> dict:
            """
            Create a Monitor entry which is simply a combination of detector_id and feed_cam
            :param name: The unique name for the new Monitor
            :param detector_id: The id of the detector
            :param feed_cam: The cam id of the feed
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
                    return {'success': True, 'monitor': Monitor.objects.create(name=name, detector=detector, feed=feed), 'message': "New monitor created."}
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

            mon_obj = None
            try:
                mon_obj = Monitor.objects.get(pk=monitor_name)
                return {'success': True, 'monitor': mon_obj, 'message': "Monitor successfully retrieved."}
            except Monitor.DoesNotExist:
                return {'success': False, 'monitor': None, 'message': f"Monitor with name '{monitor_name}' does not exist."}