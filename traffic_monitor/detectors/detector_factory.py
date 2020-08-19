import logging
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

        @staticmethod
        def get(**kwargs) -> dict:
            """
            Returns Detector object.
            Update this function to add new detection models.
            New models will require new class that inherits from Detector class.
            """
            # get supported detector from db
            try:
                obj = Detector.objects.get(detector_id=kwargs.get('detector_id'))
                if obj.name == 'cvlib':
                    detector = DetectorCVlib(**kwargs)

                    return {'success': True, 'detector': detector}
            except Detector.DoesNotExist as e:
                return {'success': False, 'message': f"Detector not setup: {kwargs.get('detector_id')} \n Available Detectors: \n {[x.detector_id for x in Detector.objects.all()]}"}



