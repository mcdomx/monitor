import threading
import queue
import json
import logging
import traceback
import numpy as np
from abc import abstractmethod

from confluent_kafka import Producer

from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.elapsed_time import ElapsedTime

logger = logging.getLogger('detector')


class DetectorMachineAbstract(ServiceAbstract):
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
                 monitor_config: dict,
                 output_data_topic: str,
                 input_image_queue: queue.Queue,
                 output_image_queue: queue.Queue):

        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.monitor_name: str = monitor_config.get('monitor_name')
        self.detector_name: str = monitor_config.get('detector_name')
        self.detector_model: str = monitor_config.get('detector_model')
        self.name: str = f"{self.detector_name}:{self.detector_model}:"
        self.input_image_queue: queue.Queue = input_image_queue
        self.output_image_queue: queue.Queue = output_image_queue
        self.output_data_topic: str = output_data_topic
        self.is_ready = True
        self.producer = Producer({'bootstrap.servers': '127.0.0.1:9092',
                                  'group.id': 'monitorgroup'})

        # # This service does not use the consumer that is setup by the
        # # serviceabstract class.  If we don't close it, Kafka will close
        # # the group when it sees that a consumer is no longer consuming.
        # self.consumer.close()

    def __str__(self):
        return f"Detector: {self.name}"

    def delivery_report(self, err, msg):
        """ Kafka support function.  Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            logger.info(f'{self.__class__.__name__}: Message delivery failed: {err}')
        else:
            logger.info(f'{self.__class__.__name__}: Message delivered to {msg.topic()} partition:[{msg.partition()}]')

    def handle_message(self, msg):
        return None

    def run(self):
        logger.info(f"Started {self.name}")

        timer = ElapsedTime()

        while self.running:

            # keep the consumer alive by regular polling
            if timer.get() > 5:
                _ = self.poll_kafka(0)
                timer.reset()

            try:
                frame = self.input_image_queue.get(block=False)

            except queue.Empty:
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

            except queue.Full:
                logger.info(f"[{self.name}] Detected frame queue was full.  Purging oldest item to make room.")
                _ = self.output_image_queue.get()
                self.output_image_queue.put({'frame': frame})
            except Exception as e:
                logger.info(f"[{self.name}] Unhandled Exception placing detection image on queue: {e.args}")

            # publish the data to kafka topic
            try:
                self.producer.poll(0)
                # prepare data for serialization
                detections = [d.replace(' ', '_') for d in detections]

                self.producer.produce(topic=self.monitor_name,
                                      key='detector_detection',
                                      value=json.JSONEncoder().encode(detections),
                                      callback=self.delivery_report,
                                      )
                self.producer.flush()

            except Exception as e:
                logger.info(f"[{self.name}] Unhandled Exception publishing detection data: {e.args}")
                logger.info(traceback.print_stack())

            # # sleep to let the timer expire
            # time.sleep(max(0, self.detection_interval - timer.get()))
            # timer.reset()
            self.is_ready = True

        self.is_ready = True  # if this stopped with is_ready as false, we make sure it will start again as ready
        self.consumer.close()
        logger.info(f"'{self.monitor_name}' '{self.detector_name}:{self.detector_model}' thread stopped!")

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
