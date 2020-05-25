import logging

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from traffic_monitor.detectors.detector_cvlib import DetectorCVlib
from traffic_monitor.models.model_detector import Detector


class DetectorFactory:
    singelton = None

    def __new__(cls):
        if cls.singelton is None:
            cls.singelton = cls._Singleton()
        return cls.singelton

    # def get(self, detector_name: str, model: str = None):
    #     return self.singelton.get(detector_name, model)

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('detector')
            self.detectors = {}

        def get(self, detector_id) -> dict:
            """
            Returns Detector object.
            Update this function to add new detection models.
            New models will require new class that inherits from Detector class.
            """
            detector_name, detector_model = detector_id.split('__')

            # see if this detector is currently loaded
            if detector_id not in self.detectors.keys():
                if detector_name == 'detector_cvlib':
                    # DetectorCVlib will create db entry, if needed
                    d = DetectorCVlib(name=detector_name, model=detector_model)
                else:
                    self.logger.info("Model not supported: {}".format(detector_name))
                    return {'success': False, 'message': "Detector not supported: {}".format(detector_name)}

                self.detectors.update({detector_id: {'id': d.id,
                                                     'name': d.name,
                                                     'model': d.model,
                                                     'detector': d}})

            # if we were able to build the detector or it was already loaded, return it
            return {'success': True, 'detector': self.detectors.get(detector_id)}
