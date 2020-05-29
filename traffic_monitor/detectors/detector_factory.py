import logging
import queue
from traffic_monitor.detectors.detector_cvlib import DetectorCVlib
from traffic_monitor.models.model_detector import Detector


class DetectorFactory:
    singelton = None

    def __new__(cls):
        if cls.singelton is None:
            cls.singelton = cls._Singleton()
        return cls.singelton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('detector')

        def get(self, detector_id: str,
                queue_detready: queue.Queue,
                queue_detframe: queue.Queue,
                mon_objs: list,
                log_objs: list) -> dict:
            """
            Returns Detector object.
            Update this function to add new detection models.
            New models will require new class that inherits from Detector class.
            """
            # get supported detector from db
            try:
                obj = Detector.objects.get(detector_id=detector_id)
                if obj.name == 'cvlib':
                    detector = DetectorCVlib(detector_id=detector_id,
                                             queue_detready=queue_detready,
                                             queue_detframe=queue_detframe,
                                             log_objs=mon_objs,
                                             mon_objs=log_objs)

                    return {'success': True, 'detector': obj, 'class': detector}
            except Detector.DoesNotExist as e:
                return {'success': False, 'message': f"Detector not setup: {detector_id} \n Available Detectors: \n {[x.detector_id for x in Detector.objects.all()]}"}



