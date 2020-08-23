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
                return Detector.objects.get(detector_id=detector_id).__dict__
            except Detector.DoesNotExist as e:
                raise Exception(f"Detector not setup: {detector_id} \n Available Detectors: \n {[x.detector_id for x in Detector.objects.all()]}")

        @staticmethod
        def get_detectors() -> list:
            try:
                return list(Detector.objects.all().values())
            except Exception:
                raise Exception(f"Failed to retrieve detector_machines")
