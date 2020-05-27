import logging
from abc import ABC, abstractmethod
import numpy as np
import threading
import queue

from traffic_monitor.models.model_class import Class

logger = logging.Logger('detector')

class Detector_Abstract(ABC, threading.Thread):
    """
    Abstract class for a detector.
    required methods:
    > detect(frame_num:int, frame:np.array) -> int, np.array
        - returns the frame number and frame with detections
    """

    def __init__(self, detector_id: str, queue_detready: queue.Queue, queue_detframe: queue.Queue):
        threading.Thread.__init__(self)
        name, model = detector_id.split('__')
        self.name = name.replace(' ', '_')
        self.model = model
        self.detector_id = detector_id
        self.is_ready = True
        self.running = False
        self.queue_detready = queue_detready
        self.queue_detframe = queue_detframe

        self.monitored_objects = None
        self.logged_objects = None

    def __str__(self):
        return "Detector: {} // {}".format(self.name, self.model)

    def start(self):
        logger.info("Starting detector ... ")
        self.running = True
        self.is_ready = True
        threading.Thread.start(self)

    def stop(self):
        logger.info("Stopping detector ... ")
        self.running = False

    def run(self):
        logger.info(f"Started {self.name} .. ")
        while self.running:

            try:
                logger.info("trying...")
                frame = self.queue_detready.get(block=True, timeout=1)

            except Exception as e:
                logger.info("timed out...")
                continue

            self.is_ready = False
            f_num, frame, log_detections, mon_detections = self.detect(frame)

            # put detected frame and detections list on queue
            self.queue_detframe.put({'frame': frame,
                                     'log_detections': log_detections,
                                     'mon_detections': mon_detections})

            self.is_ready = True

        logger.info(f"'{self.name}' thread stopped!")

    @abstractmethod
    def detect(self, frame: np.array) -> (int, np.array, list, list):
        """
        Each supported detector must override this method.
        :frame: np.array) - frame from which to detect objects
        :det_objs: set - set of object names which should be detected
        Returns: frame number, frame, log_detections list and mon_detections list
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
