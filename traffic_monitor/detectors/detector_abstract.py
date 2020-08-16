import logging
from abc import ABC, abstractmethod
import numpy as np
import threading
import queue
import time
import logging

from traffic_monitor.models.model_class import Class
from traffic_monitor.services.elapsed_time import ElapsedTime

logger = logging.getLogger('detector')


class Detector_Abstract(ABC, threading.Thread):
    """
    Abstract class for a detector.
    required methods:
    > detect(frame_num:int, frame:np.array) -> int, np.array
        - returns the frame number and frame with detections
    """

    def __init__(self, detector_id: str,
                 queue_detready: queue.Queue,
                 queue_detframe: queue.Queue,
                 queue_dets_log: queue.Queue,
                 queue_dets_mon: queue.Queue,
                 mon_objs: list, log_objs: list,
                 detection_interval: int):

        threading.Thread.__init__(self)
        self.logger = logging.Logger('detector')
        name, model = detector_id.split('__')
        self.name = name.replace(' ', '_')
        self.model = model
        self.detector_id = detector_id
        self.is_ready = True
        self.running = False
        self.queue_detready = queue_detready
        self.queue_detframe = queue_detframe
        self.queue_dets_log = queue_dets_log
        self.queue_dets_mon = queue_dets_mon

        self.monitored_objects = mon_objs
        self.logged_objects = log_objs
        self.detection_interval = detection_interval

    def __str__(self):
        return "Detector: {} // {}".format(self.name, self.model)

    def set_logged_objects(self, logged_objects: list):
        self.logged_objects = logged_objects

    def set_monitored_objects(self, monitored_objects):
        self.monitored_objects = monitored_objects

    def start(self):
        self.logger.info("Starting detector ... ")
        self.running = True
        self.is_ready = True
        threading.Thread.start(self)

    def stop(self):
        self.logger.info("Stopping detector ... ")
        self.running = False
        self.logger.info(f"Stopping detector ... Set running to {self.running}")

    def run(self):
        self.logger.info(f"Started {self.name} .. ")
        timer = ElapsedTime()
        while self.running:
            try:
                frame = self.queue_detready.get(block=False)

            except Exception as e:
                # no frames available to perform detection on
                continue

            self.is_ready = False
            try:
                f_num, frame, log_detections, mon_detections = self.detect(frame)
            except Exception as e:
                continue

            # put detected frame and detections list on queue
            try:
                self.queue_detframe.put({'frame': frame})
            except queue.Full:
                logger.info("Detected Frame queue was full.  Purging oldest item to make room.")
                _ = self.queue_detframe.get()
                self.queue_detframe.put({'frame': frame})
            except Exception as e:
                logger.info(f"Unhandled Exception: {e}")

            try:
                self.queue_dets_log.put(log_detections)
                # self.queue_dets_mon.put(mon_detections)
            except queue.Full:
                logger.info("Detections queue was full.  Purging oldest item to make room.")
                _ = self.queue_dets_log.get()
                self.queue_dets_log.put(log_detections)
            except Exception as e:
                logger.info(f"Unhandled Exception: {e}")



            # sleep to let the timer expire
            time.sleep(max(0, self.detection_interval-timer.get()))
            timer.reset()
            self.is_ready = True

        self.logger.info(f"'{self.name}' thread stopped!")

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

    @staticmethod
    def get_class_data(monitor_id: int):
        return Class.objects.filter(monitor_id=monitor_id).values()
