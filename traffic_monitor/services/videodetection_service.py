"""
A streaming service has the task of placing data from the stream
on a queue.

This is a service that will take images from a video stream
and run image detection on them.

The resulting images will be placed on a queue.

The detection service will return detections of all objects that it has been trained
to detect.  The detected image will also highlight all trained objects that are detected.

Any services that use the data will have the task of only processing data that the
service has been configured to process.

"""

import queue
import logging
from abc import ABC

import cv2 as cv

from traffic_monitor.detector_machines.detetor_machine_factory import DetectorMachineFactory
from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.elapsed_time import ElapsedTime

BUFFER_SIZE = 512

logger = logging.getLogger('videodetection_service')


class VideoDetectionService(ServiceAbstract, ABC):
    """


    """

    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str,  # Kafka topic to produce data to
                 ):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.monitor_name: str = monitor_config.get('monitor_name')
        self.name = f"VideoDetectionService-{self.monitor_name}"
        self.input_image_queue: queue.Queue = queue.Queue(BUFFER_SIZE)
        self.output_image_queue: queue.Queue = queue.Queue(BUFFER_SIZE)

        # DETECTOR STATES
        self.show_full_stream = False

        # Create a detector
        self.detector = DetectorMachineFactory().get_detector_machine(monitor_config=monitor_config,
                                                                      input_image_queue=self.input_image_queue,
                                                                      output_image_queue=self.output_image_queue,
                                                                      output_data_topic=self.output_data_topic)

        # # This service does not use the consumer that is setup by the
        # # serviceabstract class.  If we don't close it, Kafka will close
        # # the group when it sees that a consumer is no longer consuming.
        # self.consumer.close()

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    def get_next_frame(self):
        q = self.output_image_queue.get()
        return q.get()

    def handle_message(self, msg):
        return None

    def run(self):
        """
        This will start the service by calling threading.Thread.start()
        Frames will be placed in respective queues.
        """
        # set source of video stream
        try:
            cap = cv.VideoCapture(self.monitor_config.get('feed_url'))

            # start the detector machine
            self.detector.start()

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Failed to create a video stream.")
            logger.error(e)
            return

        logger.info(f"Starting video detection service for id: {self.monitor_name}")
        logger.info(f"Video detection service running for {self.monitor_name}: {self.running}")
        logger.info(f"Video Capture Opened: {cap.isOpened()}")

        timer = ElapsedTime()

        while self.running and cap.isOpened():

            # keep the consumer alive by regular polling
            if timer.get() > 5:
                _ = self.poll_kafka(0)
                timer.reset()

            cap.grab()  # only read every other frame
            success, frame = cap.read()

            # if detector is ready, place frame in
            # queue for the detector to pick up
            if success:

                # if the detector stopped for some reason, create a new thread
                if not self.detector.is_alive():
                    logger.info(f"Restarting {self.monitor_config.get('detector_name')}:{self.monitor_config.get('detector_model')} for {self.monitor_name}")
                    self.detector = DetectorMachineFactory().get_detector_machine(monitor_config=self.monitor_config,
                                                                                  input_image_queue=self.input_image_queue,
                                                                                  output_image_queue=self.output_image_queue,
                                                                                  output_data_topic=self.output_data_topic)
                    self.detector.start()

                # if detector is ready, perform frame detection
                if self.detector.is_ready:
                    try:
                        # the detector will perform detection on this
                        # image and place the resulting image on the
                        # output_image_queue and detection data on
                        # output_data_queue
                        self.input_image_queue.put(frame, block=False)

                    except queue.Full:
                        # if queue is full skip, drop an image to make room
                        _ = self.input_image_queue.get()
                        self.input_image_queue.put(frame, block=False)
                        continue

        # stop the detector service
        self.detector.stop()
        self.detector.join()

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped video detection service.")

    @staticmethod
    def get_trained_objects(detector_name) -> list:
        return DetectorMachineFactory().get_trained_objects(detector_name)
