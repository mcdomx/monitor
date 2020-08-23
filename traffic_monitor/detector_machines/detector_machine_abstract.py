import threading
import queue
import time
import logging
import numpy as np
from abc import ABC, abstractmethod, ABCMeta

from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.elapsed_time import ElapsedTime

logger = logging.getLogger('detector')


class DetectorMachineAbstract(ServiceAbstract, metaclass=ABCMeta):
    """
    Abstract class for a detector.
    required methods:
    > detect(frame_num:int, frame:np.array) -> int, np.array
        - returns the frame number and frame with detections
    > get_trained_objects() -> set
        - returns a set of strings where each item is a trained object

    A Detector is only instantiated when a Monitor Service is created and
    the Detector instance is tied to 1:1 with a MonitorService.

    Each Detector must be configured and will inherit this Abstract Class.
    """

    def __init__(self, **kwargs):

        threading.Thread.__init__(self)
        self.logger = logging.Logger('detector')
        self.detector_id = kwargs.get('detector_id')
        self.name = kwargs.get('detector_name')
        self.model = kwargs.get('detector_model')

        self.is_ready = True
        self.running = False
        self.queue_detready = kwargs.get('queue_detready')
        self.queue_detframe = kwargs.get('queue_detframe')
        self.queue_dets_log = kwargs.get('queue_dets_log')
        self.queue_dets_mon = kwargs.get('queue_dets_mon')

        self.notified_objects = kwargs.get('notified_objects')
        self.logged_objects = kwargs.get('logged_objects')
        # self.monitor: Monitor = kwargs.get('monitor')
        self.detection_interval = kwargs.get('detection_interval')

    def __str__(self):
        return "Detector: {}".format(self.detector_id)

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

    @classmethod
    @abstractmethod
    def get_trained_objects(cls) -> list:
        """
        Each supported detector class must override this method.
        :return: set of strings where each string is the name of a trained object. Spaces
        must be represented with an underscore, '_'.
        """
        ...

