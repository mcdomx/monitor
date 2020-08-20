import logging
from traffic_monitor.detectors.detector_abstract import DetectorAbstract
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
        def _get_detector_class(detector_name) -> DetectorAbstract.__class__:
            """
            Determine the implemented detector class based on the detector name.
            Update this function to add new detection models which implement DetectorAbstract.
            :param detector_name: Name of the detector for which the corresponding class is requested
            :return: An unimplemented class reference to the detector
            """
            if detector_name == 'cvlib':
                return DetectorCVlib

        @staticmethod
        def get_trained_objects(detector_name):
            return DetectorFactory()._get_detector_class(detector_name).get_trained_objects()

        @staticmethod
        def get(**kwargs) -> dict:
            """
            Returns Detector object.
            """
            # get supported detector from db
            try:
                obj = Detector.objects.get(detector_id=kwargs.get('detector_id'))
                # if obj.name == 'cvlib':
                #     detector = DetectorCVlib(**kwargs)
                detector = DetectorFactory()._get_detector_class(obj.name)(**kwargs)
                return {'success': True, 'detector': detector}
            except Detector.DoesNotExist as e:
                return {'success': False, 'message': f"Detector not setup: {kwargs.get('detector_id')} \n Available Detectors: \n {[x.detector_id for x in Detector.objects.all()]}"}



