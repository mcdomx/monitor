import logging

from traffic_monitor.detector_machines.detector_machine_abstract import DetectorMachineAbstract
from traffic_monitor.detector_machines.detector_machines import *


class DetectorMachineFactory:
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
        return cls.singleton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('detector')

        @staticmethod
        def get_detector_machine(**kwargs) -> DetectorMachineAbstract:
            """
            Determine the implemented detector class based on the detector name.
            Update this function to add new detection models which implement DetectorAbstract.
            :param detector_name: Name of the detector for which the corresponding class is requested
            :param detector_name:
            :param kwargs:
                        detector_id
                        detector_name
                        detector_model
                        queue_detready
                        queue_detframe
                        queue_dets_log
                        queue_dets_mon
                        notified_objects
                        logged_objects
                        detection_interval
            :return: An implemented instance of a detector machine that is ready to be started with .start()
            """

            if kwargs.get('detector_name') == 'cvlib':
                return DetectorMachineCVlib(**kwargs)

        @staticmethod
        def _get_detector_class(detector_name) -> DetectorMachineAbstract.__class__:
            """
            Determine the implemented detector class based on the detector name.
            Update this function to add new detection models which implement DetectorAbstract.
            :param detector_name: Name of the detector for which the corresponding class is requested
            :return: An unimplemented class reference to the detector
            """
            if detector_name == 'cvlib':
                return DetectorMachineCVlib

        @staticmethod
        def get_trained_objects(detector_name):
            return DetectorMachineFactory()._get_detector_class(detector_name).get_trained_objects()

