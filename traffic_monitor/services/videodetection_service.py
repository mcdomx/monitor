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

import cv2 as cv

from traffic_monitor.detector_machines.detetor_machine_factory import DetectorMachineFactory
from traffic_monitor.services.service_abstract import ServiceAbstract

BUFFER_SIZE = 512

logger = logging.getLogger('videodetection_service')


class VideoDetectionService(ServiceAbstract):
    """


    """

    def __init__(self,
                 monitor_config: dict,
                 # feed_id: str,
                 # feed_url: str,
                 # time_zone: str,
                 output_data_topic: str,  # Kafka topic to produce data to
                 # output_image_queue: queue.Queue,  # this is where the service will place detected images
                 # detector_name: str,
                 # detector_model: str,
                 ):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        ServiceAbstract.__init__(self, monitor_config=monitor_config)
        self.id = id(self)
        self.monitor_name: str = monitor_config.get('monitor_name')
        self.name = f"VideoDetectionService-{self.monitor_name}"
        self.input_image_queue: queue.Queue = queue.Queue(BUFFER_SIZE)
        self.output_data_topic: str = output_data_topic
        self.output_image_queue: queue.Queue = queue.Queue(BUFFER_SIZE)
        self.detector_name = monitor_config.get('detector_name')
        self.detector_model = monitor_config.get('monitor_name')
        self.feed_url = monitor_config.get('feed_url')
        self.feed_id = monitor_config.get('feed_id')
        self.time_zone = monitor_config.get('time_zone')

        # DETECTOR STATES
        self.running = False
        self.show_full_stream = False

        # Create a detector
        self.detector = DetectorMachineFactory().get_detector_machine(monitor_name=self.monitor_name,
                                                                      detector_name=self.detector_name,
                                                                      detector_model=self.detector_model,
                                                                      input_image_queue=self.input_image_queue,
                                                                      output_image_queue=self.output_image_queue,
                                                                      output_data_topic=self.output_data_topic)

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    def get_next_frame(self):
        q = self.output_image_queue.get()
        return q.get()

    def update(self, context: dict):
        # do something here
        ServiceAbstract.update(self, context)

    def start(self) -> dict:
        """
        Overriding Threading.start() so that we can test if a monitor service  is already active for
        the monitor and set the 'running' variable.
        :return: A dict with bool 'success' and string 'message' describing result.
        """
        if self.running:
            message = {'message': f"[{__name__}] Service is already running: {self.monitor_name}"}
            return message
        try:
            self.running = True
            # threading.Thread.start(self)
            ServiceAbstract.start(self)
            message = {'message': f"[{__name__}] Service started for: {self.monitor_name}"}
            return message
        except Exception as e:
            raise Exception(f"[{__name__}] Could not start '{self.monitor_name}': {e}")

    def stop(self):
        self.running = False
        logger.info(f"[{__name__}] Stopped.  Set running to False.")

    def run(self):
        """
        This will start the service by calling threading.Thread.start()
        Frames will be placed in respective queues.
        """
        # set source of video stream
        try:
            cap = cv.VideoCapture(self.feed_url)
        except Exception as e:
            logger.error(f"[{__name__}] Failed to create a video stream.")
            logger.error(e)
            return

        # The detector is handled separately from the other sub-services
        # start the detector machine
        self.detector.start()
        # register monitor_service with detector to get detector updates

        logger.info(f"Starting video detection service for id: {self.monitor_name}")
        logger.info(f"Video detection service running for {self.monitor_name}: {self.running}")
        logger.info(f"Video Capture Opened: {cap.isOpened()}")
        while self.running and cap.isOpened():

            cap.grab()  # only read every other frame
            success, frame = cap.read()

            # if detector is ready, place frame in
            # queue for the detector to pick up
            if success:

                # if detector is ready, perform frame detection
                if self.detector.is_ready:
                    try:
                        # the detector will perform detection on this
                        # image and place the resulting image on the
                        # output_image_queue and detection data on
                        # output_data_queue
                        self.input_image_queue.put(frame, block=False)

                        # target_queue = self.queue_detframe
                    except queue.Full:
                        # if queue is full skip, drop an image to make room
                        _ = self.input_image_queue.get()
                        self.input_image_queue.put(frame, block=False)
                        continue

                # elif self.show_full_stream:  # just use the raw frame from feed without detection
                #     try:
                #         self.queue_rawframe.put({'frame': frame}, block=False)
                #         target_queue = self.queue_rawframe
                #     except queue.Full:
                #         continue  # if queue is full skip
                # else:
                #     continue
                #
                # # Now, update the reference queue with the type of frame
                # if self.display:
                #     try:
                #         self.queue_refframe.put(target_queue, block=False)
                #     except queue.Full:
                #         # if q is full, remove next item to make room
                #         logger.info("Ref Queue Full!  Making room.")
                #         _ = self.get_next_frame()
                #         self.queue_refframe.put(target_queue, block=False)

        logger.info(f"[{self.monitor_name}] Stopped monitor service")

        # stop the services
        self.detector.stop()

        # for s in self.active_services:
        #     s: ServiceAbstract = s
        #     s.stop()
        #
        # for s in self.active_services:
        #     s: ServiceAbstract = s
        #     s.join()
        #
        # self.active_services = []

        self.detector.join()

        logger.info(f"[{self.monitor_name}] Video Service and its detector are stopped!")

    @staticmethod
    def get_trained_objects(detector_name) -> list:
        return DetectorMachineFactory().get_trained_objects(detector_name)
