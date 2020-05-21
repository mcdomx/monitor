import logging
from abc import ABC, abstractmethod
import numpy as np


class Detector_Abstract(ABC):
    """
    Abstract class for a detector.
    required methods:
    > detect(frame_num:int, frame:np.array) -> int, np.array
        - returns the frame number and frame with detections
    """

    def __init__(self, name: str, model: str = None, verbosity: int = 0):
        self.name = name.replace(' ', '_')
        self.model = model
        self.id = f"{name}__{model}"
        self.logger = logging.Logger('detector')

    def __str__(self):
        return "Detector: {} // {}".format(self.name, self.model)

    @abstractmethod
    def detect(self, frame: np.array) -> (int, np.array, list):
        """
        Each supported detector must override this method.
        :frame: np.array) - frame from which to detect objects
        :det_objs: set - set of object names which should be detected
        Returns frame number, frame and detections
        """
        ...

    @abstractmethod
    def get_trained_objects(self) -> set:
        """
        Each supported detector must override this method.
        :return: set of strings where each string is the name of a trained object. Spaces
        must be represented with an underscore, '_'.
        """
        ...
