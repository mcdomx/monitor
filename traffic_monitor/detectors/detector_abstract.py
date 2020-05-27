import logging
from abc import ABC, abstractmethod
import numpy as np

from traffic_monitor.models.model_class import Class


class Detector_Abstract(ABC):
    """
    Abstract class for a detector.
    required methods:
    > detect(frame_num:int, frame:np.array) -> int, np.array
        - returns the frame number and frame with detections
    """

    def __init__(self, detector_id: str, verbosity: int = 0):
        name, model = detector_id.split('__')
        self.name = name.replace(' ', '_')
        self.model = model
        self.detector_id = detector_id
        self.logger = logging.Logger('detector')

        self.monitored_objects = None
        self.logged_objects = None

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

    def load_classes(self):
        classes = self.get_trained_objects()
        for class_name in classes:
            Class.create(class_name=class_name, detector_id=self.detector_id, monitor=True, log=True)

    def update_monitored_objects(self):
        self.monitored_objects = Class.get_monitored_objects(self.detector_id)

    def update_logged_objects(self):
        self.logged_objects = Class.get_logged_objects(self.detector_id)

    @staticmethod
    def get_class_data(detector_id: str):
        return Class.objects.filter(detector_id=detector_id).values()

    def toggle_monitor(self, class_id):
        rv = Class.toggle_mon(class_id=class_id, detector_id=self.detector_id)
        self.update_monitored_objects()
        return rv

    def toggle_log(self, class_id):
        rv = Class.toggle_log(class_id=class_id, detector_id=self.detector_id)
        self.update_logged_objects()
        return rv

    def toggle_all_mon(self):
        rv = Class.toggle_all_mon(self.detector_id)
        self.update_monitored_objects()
        return rv

    def toggle_all_log(self):
        rv = Class.toggle_all_log(self.detector_id)
        self.update_logged_objects()
        return rv
