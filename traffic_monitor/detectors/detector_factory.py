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

        def get(self, detector_id) -> dict:
            """
            Returns Detector object.
            Update this function to add new detection models.
            New models will require new class that inherits from Detector class.
            """
            # get supported detector from db
            try:
                obj = Detector.objects.get(pk=detector_id)
                return {'success': True, 'detector': DetectorCVlib(detector_id=obj.detector_id)}
            except Detector.DoesNotExist as e:
                return {'success': False, 'message': "Detector not setup: {}".format(detector_id)}



