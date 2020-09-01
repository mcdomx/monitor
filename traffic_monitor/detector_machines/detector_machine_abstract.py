import threading
import queue
# import time
import logging
import numpy as np
from abc import abstractmethod, ABCMeta

from confluent_kafka import Producer

from traffic_monitor.services.service_abstract import ServiceAbstract
# from traffic_monitor.services.elapsed_time import ElapsedTime

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

    ---REVSIED--
    A detector has the task of retrieving images from a queue, and then
    performing object detection.  The resulting image is placed on an
    image queue and the detected objects are placed on a data queue.
    """

    def __init__(self,
                 monitor_name: str,
                 detector_name: str,
                 detector_model: str,
                 input_image_queue: queue.Queue,
                 output_image_queue: queue.Queue,
                 output_data_topic: str):

        threading.Thread.__init__(self)
        self.monitor_name: str = monitor_name
        self.detector_name: str = detector_name
        self.detector_model: str = detector_model
        self.name: str = f"{detector_name}:{detector_model}:"
        self.input_image_queue: queue.Queue = input_image_queue
        self.output_image_queue: queue.Queue = output_image_queue
        self.output_data_topic: str = output_data_topic

        self.is_ready = True
        self.running = False
        # self.queue_detready = kwargs.get('queue_detready')
        # self.queue_detframe = kwargs.get('queue_detframe')
        # self.queue_dets_log = kwargs.get('queue_dets_log')
        # self.queue_dets_mon = kwargs.get('queue_dets_mon')
        # self.detection_interval = kwargs.get('detection_interval')

    def __str__(self):
        return f"Detector: {self.name}"

    def start(self):
        logger.info(f"Starting detector '{self.name}' ...")
        self.running = True
        self.is_ready = True
        ServiceAbstract.start(self)

    def stop(self):
        self.running = False
        # in case the detector stops from a local error
        self.publish({'subject': 'detector_action',
                      'message': f"{self.detector_name} was stopped.",
                      'function': 'stop',
                      'kwargs': None})
        logger.info(f"Stopping detector '{self.name}' ...")

    def delivery_report(self, err, msg):
        """ Kafka support function.  Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            logger.info(f'{self.detector_model}: Message delivery failed: {err}')
        else:
            logger.info(f'{self.detector_model}: Message delivered to {msg.topic()} [{msg.partition()}]')

    def run(self):
        logger.info(f"Started {self.name}")
        # timer = ElapsedTime()
        producer = Producer({'bootstrap.servers': '127.0.0.1'})
        while self.running:
            try:
                # frame = self.queue_detready.get(block=False)
                frame = self.input_image_queue.get(block=False)

            except queue.Empty as e:
                # no frames available to perform detection on
                continue

            self.is_ready = False
            try:
                frame, detections = self.detect(frame)
            except Exception as e:
                logger.info(f"[{self.name}] Unhandled Detection Exception: {e.args}")
                continue

            # put detected frame on queue
            try:
                self.output_image_queue.put({'frame': frame})
                # self.publish({
                #     'subject': self.monitor_name,
                #     'function': 'detected_image',
                #     'kwargs': {'image': frame}
                # })
            except queue.Full:
                logger.info(f"[{self.name}] Detected frame queue was full.  Purging oldest item to make room.")
                _ = self.output_image_queue.get()
                self.output_image_queue.put({'frame': frame})
            except Exception as e:
                logger.info(f"[{self.name}] Unhandled Exception placing detection image on queue: {e.args}")

            # publish the data to kafka topic
            try:
                producer.poll(0)
                # prepare data for serialization
                detections = [d.replace(' ', '_') for d in detections]

                # publish detections using kafka
                producer.produce(topic=self.monitor_name,
                                 key='detections',
                                 value=' '.join(detections).encode('utf-8'),
                                 callback=self.delivery_report,
                                 )
                producer.flush()
                # self.output_data_queue.put(detections)
            # except queue.Full:
            #     logger.info(f"[{self.name}] Detections data queue was full.  Purging oldest item to make room.")
            #     _ = self.output_data_queue.get()
            #     self.output_data_queue.put(detections)
            except Exception as e:
                logger.info(f"[{self.name}] Unhandled Exception publishing detection data: {e.args}")

            # # sleep to let the timer expire
            # time.sleep(max(0, self.detection_interval - timer.get()))
            # timer.reset()
            self.is_ready = True

        logger.info(f"'{self.name}' thread stopped!")

    @abstractmethod
    def detect(self, frame: np.array) -> (np.array, list):
        """
        Each supported detector must override this method.
        :frame: np.array) - frame from which to detect objects
        :det_objs: set - set of object names which should be detected
        Returns: frame number, frame, list of all items detected
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

    def update(self, subject_info: tuple):
        logger.info(f"[{self.__name__}] UPDATED: {subject_info}")
