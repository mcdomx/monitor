"""
This is the top level service for a feed.  This service contains
all the information and supporting services that will execute
a feed, display the feed and log its data.
"""

import queue
import logging

# import cv2 as cv

from confluent_kafka.admin import AdminClient, NewTopic, KafkaException

from traffic_monitor.detector_machines.detetor_machine_factory import DetectorMachineFactory
# from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.videodetection_service import VideoDetectionService
from traffic_monitor.services.log_service import LogService
from traffic_monitor.services.notification_service import NotificationService
from traffic_monitor.services.chart_service import ChartService
from traffic_monitor.services.observer import Observer

BUFFER_SIZE = 512

logger = logging.getLogger('monitor_service')


class MonitorService(Observer):
    """
    A Monitor is defined as a Detector and a URL video feed.
    The class is a thread that will continually run and log
    data whether the application is displaying the video
    feed or not.

    The Monitor will handle getting streaming images from a
    url and performing detections.  Since detections cannot be
    performed on each frame, the service will determine when
    the detector is ready to perform a new detection and only
    return detection frames when it is able to.

    When running, the feed service will place frames in a queue.
    If the frame includes detections, it will also show the
    detections in the image frame.  If the application is set to
    display the feed from the Monitor, the application can
    get the images to display from the queue of images.

    The MonitorService runs as a thread.  When the thread starts,
    the MonitorService adds itself to the ActiveMonitors singleton.

    ActiveMonitors is a class that hold information about active
    monitors and its largest task is to provide a source for the
    actively running monitors.  The ActiveMonitors class can
    also turn on and off a Monitor's ability to display the visual feed.

    """

    def __init__(self,
                 monitor_config: dict,
                 ):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        Observer.__init__(self)
        self.id = id(self)
        self.monitor_config: dict = monitor_config

        self.monitor_name: str = monitor_config.get('monitor_name')
        # # self.name = f"MonitorServiceThread-{self.monitor_name}"
        # # self.detector_id = monitor_config.get('detector_id')
        # self.detector_name: str = monitor_config.get('detector_name')
        # self.detector_model: str = monitor_config.get('detector_model')
        # self.feed_url: str = monitor_config.get('feed_url')
        # self.feed_id: str = monitor_config.get('feed_id')
        # self.time_zone: str = monitor_config.get('time_zone')
        self.output_data_topic: str = self.monitor_name
        # # self.detection_interval: int = detection_interval
        # self.charting_on: bool = monitor_config.get('charting_on')
        # # self.charting_interval: int = charting_interval
        # self.logging_on: bool = monitor_config.get('logging_on')
        # self.log_objects: list = monitor_config.get('log_objects')
        # # self.log_interval: int = log_interval
        # self.notifications_on: bool = monitor_config.get('notifications_on')
        # self.notified_objects: list = monitor_config.get('notified_objects')
        # # self.notification_interval = notification_interval
        #
        # # self.services: list = services

        # DETECTOR STATES
        self.running = False
        self.show_full_stream = False
        self.display = False

        # QUEUES
        self.output_image_queue = queue.Queue(BUFFER_SIZE)

        # self.queue_rawframe = queue.Queue(BUFFER_SIZE)
        # self.queue_detframe = queue.Queue(BUFFER_SIZE)
        # self.queue_detready = queue.Queue(BUFFER_SIZE)
        # self.queue_refframe = queue.Queue(BUFFER_SIZE)
        # self.queue_dets_not = queue.Queue(BUFFER_SIZE)
        # self.queue_dets_log = queue.Queue(BUFFER_SIZE)

        # Monitor Service Parameters

        # self.log_channel_url: str = '/ws/traffic_monitor/log/'

        self.active_services = []

        # self.subject_name = f"monitor_service__{self.monitor_name}"

        # set arguments used to start monitor
        # self.service_kwargs = {
        #     'monitor_name': self.monitor_name,
        #     'time_zone': self.time_zone,
        #     'detector_id': self.detector_id,
        #     'detector_name': self.detector_name,
        #     'detector_model': self.detector_model,
        #     'queue_detready': self.queue_detready,
        #     'queue_detframe': self.queue_detframe,
        #     'queue_dets_log': self.queue_dets_log,
        #     'queue_dets_mon': self.queue_dets_not,
        #     # 'notified_objects': self.notified_objects,
        #     'log_objects': self.log_objects,
        #     'log_interval': self.log_interval,
        #     'detection_interval': self.detection_interval,
        #     'charting_interval': self.charting_interval
        # }

        # the detector is handled separately from the sub-services because
        # it is a required element of the monitor service to function properly
        # self.detector = DetectorMachineFactory().get_detector_machine(**self.service_kwargs)

        # SETUP KAFKA TOPIC
        # Create a dedicated Kafka topic for this monitor service.
        # This topic is used by the sub-services of this monitor
        # to communicate with each other.
        # https://github.com/confluentinc/confluent-kafka-python
        a = AdminClient({'bootstrap.servers': '127.0.0.1'})
        topic = NewTopic(self.monitor_name, num_partitions=3, replication_factor=1)

        # Call create_topics to asynchronously create topics. {topic,future} is returned.
        fs = a.create_topics([topic])

        # Wait for each operation to finish.
        for t, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} created".format(t))
            except KafkaException as e:
                logger.info("Did not create topic {}: {}".format(t, e))
            except Exception as e:
                logger.info("Unhandled error when creating topic {}: {}".format(t, e))

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    def get_next_frame(self):
        q = self.output_image_queue.get()
        return q.get()

    def update(self, context):
        # {
        #  'subject': 'monitor_name',
        #  'function': 'set_value',
        #  'kwargs': {field: value}}
        # looking for published images
        if context.get('subject') == self.monitor_name:
            if context.get('function') == 'detected_image':
                try:
                    self.output_image_queue.put(context.get('kwargs').get('image'), block=False)
                except queue.Full:
                    # make room
                    _ = self.output_image_queue.get(block=False)
                    self.output_image_queue.put(context.get('kwargs').get('image'), block=False)

                logger.info(f"[{__name__}] Put image on queue: {self.monitor_name}")

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
            # Start Services
            vds = VideoDetectionService(monitor_config=self.monitor_config,
                                        output_data_topic=self.output_data_topic)
            self.active_services.append(vds)

            ls = LogService(monitor_config=self.monitor_config,
                            output_data_topic=self.output_data_topic)
            self.active_services.append(ls)

            ns = NotificationService(monitor_config=self.monitor_config,
                                     output_data_topic=self.output_data_topic)
            self.active_services.append(ns)

            cs = ChartService(monitor_config=self.monitor_config,
                              output_data_topic=self.output_data_topic)
            self.active_services.append(cs)

            # start sub-services
            for s in self.active_services:
                s.start()

            self.running = True
            # threading.Thread.start(self)
            # ServiceAbstract.start(self)
            return {'message': f"[{__name__}] Service started for: {self.monitor_name}"}

        except Exception as e:
            raise Exception(f"[{__name__}] Could not start '{self.monitor_name}': {e}")

    def stop(self) -> dict:
        for s in self.active_services:
            s.stop()

        for s in self.active_services:
            s.join()

        message = {'message': f"[{__name__}] Stopped."}

        self.running = False
        logger.info(message.get('message'))
        return message

    # def start_service(self, s):
    #     # s: ServiceAbstract = service_class(**self.service_kwargs)
    #     s.start()
    #     self.active_services.append(s)

    # def run(self):
    #     """
    #     This will start the service by calling threading.Thread.start()
    #     Frames will be placed in respective queues.
    #     """
    #     # # set source of video stream
    #     # try:
    #     #     cap = cv.VideoCapture(self.feed_url)
    #     # except Exception as e:
    #     #     logger.error(f"[{__name__}] Failed to create a video stream.")
    #     #     logger.error(e)
    #     #     return
    #
    #
    #
    #     # # The detector is handled separately from the other sub-services
    #     # # start the detector machine
    #     # self.detector.start()
    #     # # register monitor_service with detector to get detector updates
    #     # # TODO: This may be better handled with kafka messaging
    #     # self.detector.register(self)
    #
    #
    #
    #     logger.info(f"Starting monitoring service for id: {self.monitor_name}")
    #     logger.info(f"Monitor Service Running for {self.monitor_name}: {self.running}")
    #     # logger.info(f"Video Capture Opened: {cap.isOpened()}")
    #     while self.running:
    #
    #         cap.grab()  # only read every other frame
    #         success, frame = cap.read()
    #
    #         # if detector is ready, place frame in queue for the
    #         # detector to pick up, else put in raw frame queue.
    #         if success:
    #
    #             # if detector is ready, perform frame detection
    #             if self.detector.is_ready:
    #                 try:
    #                     self.queue_detready.put(frame, block=False)
    #                     target_queue = self.queue_detframe
    #                 except queue.Full:
    #                     continue  # if queue is full skip
    #
    #             elif self.show_full_stream:  # just use the raw frame from feed without detection
    #                 try:
    #                     self.queue_rawframe.put({'frame': frame}, block=False)
    #                     target_queue = self.queue_rawframe
    #                 except queue.Full:
    #                     continue  # if queue is full skip
    #             else:
    #                 continue
    #
    #             # Now, update the reference queue with the type of frame
    #             if self.display:
    #                 try:
    #                     self.queue_refframe.put(target_queue, block=False)
    #                 except queue.Full:
    #                     # if q is full, remove next item to make room
    #                     logger.info("Ref Queue Full!  Making room.")
    #                     _ = self.get_next_frame()
    #                     self.queue_refframe.put(target_queue, block=False)
    #
    #     logger.info(f"[{self.monitor_name}] Stopped monitor service")

    # # stop the services
    # self.detector.stop()
    #
    # for s in self.active_services:
    #     s: ServiceAbstract = s
    #     s.stop()
    #
    # for s in self.active_services:
    #     s: ServiceAbstract = s
    #     s.join()
    #
    # self.active_services = []
    #
    # self.detector.join()
    #
    # logger.info(f"[{self.monitor_name}] Monitor Service and its services are all stopped!")

    @staticmethod
    def get_trained_objects(detector_name) -> list:
        return DetectorMachineFactory().get_trained_objects(detector_name)
