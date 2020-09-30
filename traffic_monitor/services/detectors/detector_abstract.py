import logging
import numpy as np
from abc import ABCMeta, abstractmethod

logger = logging.getLogger('detector')


class DetectorAbstract(metaclass=ABCMeta):
    """
    Abstract class for a detector.
    required methods:
    > detect(frame_num:int, frame:np.array) -> int, np.array
        - returns the frame number and frame with detections
    > get_trained_objects() -> set
        - returns a set of strings where each item is a trained object
    > set_detector() -> set
        - sets the values of a detector using a list of k/w pairs {'field': attribute_name_to_set, 'value': new_value_of_attribute}
        - This method will need to determine what to do with any k/w pair in the list including ignoring them.

    A detector has the task of detecting objects or patterns from data that is supplied to it.

    """

    def __init__(self, monitor_config: dict):
        self.monitor_config = monitor_config

    def __str__(self):
        return f"Detector: {self.monitor_config.get('detector_name')}-{self.monitor_config.get('detector_model')}"

    @abstractmethod
    def detect(self, frame: np.array) -> (np.array, list):
        """
        Each supported detector must override this method.
        :frame: np.array) - frame from which to detect objects
        :det_objs: set - set of object names which should be detected
        Returns: frame number, frame, list of all items detected
        """
        ...

    @abstractmethod
    def set_detector(self, kwargs_list: list):
        """ This is used to set a key/value pair in the monitor_config object.
         The implementing class will determine which elements can be changed and
         which are restricted. """
        ...

    @classmethod
    @abstractmethod
    def get_trained_objects(cls) -> list:
        """
        Each supported detector class must override this method.
        :return: set of strings where each string is the name of a trained object. Spaces
        must be represented with an underscore, '_'.
        """
        ...
