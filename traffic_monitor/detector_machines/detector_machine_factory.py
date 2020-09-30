# import logging
# import queue
#
# from traffic_monitor.detector_machines.detector_machine_abstract import DetectorMachineAbstract
# from traffic_monitor.detector_machines.detector_machines import DetectorMachineCVlib
#
# # This dictionary must be updated with new detector name and class
# # Any new class must also be imported into the traffic_monitor.detector_machines.detector_machines module
# DETECTORS = {'cvlib': DetectorMachineCVlib}
#
#
# class DetectorMachineFactory:
#     singleton = None
#
#     def __new__(cls):
#         if cls.singleton is None:
#             cls.singleton = cls._Singleton()
#         return cls.singleton
#
#     class _Singleton:
#         def __init__(self):
#             self.logger = logging.getLogger('detector')
#
#         @staticmethod
#         def get_detector_machine(monitor_config: dict,
#                                  input_image_queue: queue.Queue,
#                                  output_image_queue: queue.Queue,
#                                  output_data_topic: str) -> DetectorMachineAbstract:
#             """
#             Determine the implemented detector class based on the detector name.
#             Update this function to add new detection models which implement DetectorAbstract.
#             :param class_colors:
#             :param output_data_topic:
#             :param monitor_config:
#             :param input_image_queue:
#             :param output_image_queue:
#
#             :return: An implemented instance of a detector machine that is ready to be started with .start()
#             """
#
#             detector_class: DetectorMachineAbstract.__class__ = DetectorMachineFactory()._get_detector_class(
#                 monitor_config.get('detector_name'))
#
#             return detector_class(monitor_config=monitor_config,
#                                   input_image_queue=input_image_queue,
#                                   output_image_queue=output_image_queue,
#                                   output_data_topic=output_data_topic)
#
#         @staticmethod
#         def _get_detector_class(detector_name) -> DetectorMachineAbstract.__class__:
#             """
#             Determine the implemented detector class based on the detector name.
#             Update this function to add new detection models which implement DetectorAbstract.
#             :param detector_name: Name of the detector for which the corresponding class is requested
#             :return: An unimplemented class reference to the detector
#             """
#
#             detector_class = DETECTORS.get(detector_name)
#
#             if detector_class is None:
#                 raise Exception(
#                     f"Detector with name '{detector_name}' does not exist. Available detectors: {list(DETECTORS.keys())}")
#             else:
#                 return detector_class
#
#         @staticmethod
#         def get_trained_objects(detector_name):
#
#             return DetectorMachineFactory()._get_detector_class(detector_name).get_trained_objects()
#
#         # @staticmethod
#         # def get_class_colors(detector_name):
#         #     return DetectorMachineFactory()._get_detector_class(detector_name).get_class_colors()
