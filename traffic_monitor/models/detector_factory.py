import logging

from traffic_monitor.models.model_detector import Detector


class DetectorFactory:
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
        return cls.singleton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('detector')

        @staticmethod
        def get(detector_id: str) -> dict:
            """
            Returns Detector object.
            """
            # get supported detector from db
            try:
                obj = Detector.objects.get(detector_id=detector_id)
                return {'success': True, 'detector': obj}
            except Detector.DoesNotExist as e:
                return {'success': False, 'message': f"Detector not setup: {detector_id} \n Available Detectors: \n {[x.detector_id for x in Detector.objects.all()]}"}

        @staticmethod
        def get_detectors() -> dict:
            try:
                det_objs = Detector.objects.all()
                return {'success': True, 'detector_machines': det_objs}
            except Exception:
                return {'success': False, 'message': f"Failed to retrieve detector_machines", 'detector_machines': None}

