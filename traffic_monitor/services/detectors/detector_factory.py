import logging

from .detector_abstract import DetectorAbstract
from .detectors import DetectorCVlib

# This dictionary must be updated with new detector name and class
# Any new class must also be imported into the traffic_monitor.detector_machines.detector_machines module
DETECTORS = {'cvlib': DetectorCVlib}


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
        def get_detector(monitor_config: dict) -> DetectorAbstract:
            """
            Determine the implemented detector class based on the detector name.
            Update this function to add new detection models which implement DetectorAbstract.
            :param monitor_config:

            :return: An implemented instance of a detector machine that is ready to be started with .start()
            """

            detector_class: DetectorAbstract.__class__ = DetectorFactory()._get_class(
                detector_name=monitor_config.get('detector_name'))

            return detector_class(monitor_config=monitor_config)

        @staticmethod
        def _get_class(detector_name) -> DetectorAbstract.__class__:
            """
            Determine the implemented detector class based on the detector name.
            Update this function to add new detection models which implement DetectorAbstract.
            :param detector_name: Name of the detector for which the corresponding class is requested
            :return: An unimplemented class reference to the detector
            """

            detector_class = DETECTORS.get(detector_name)

            if detector_class is None:
                raise Exception(
                    f"Detector with name '{detector_name}' does not exist. Available detectors: {list(DETECTORS.keys())}")
            else:
                return detector_class

        @staticmethod
        def get_trained_objects(detector_name):

            return DetectorFactory()._get_class(detector_name).get_trained_objects()
