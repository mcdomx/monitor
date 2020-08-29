"""
This is the top level service for a feed.  This service contains
all the information and supporting services that will execute
a feed, display the feed and log its data.
"""

import threading
import queue
import logging

import cv2 as cv

from traffic_monitor.detector_machines.detetor_machine_factory import DetectorMachineFactory
from traffic_monitor.services.service_abstract import ServiceAbstract

BUFFER_SIZE = 512

logger = logging.getLogger('monitor_service')


class MonitorService(ServiceAbstract):
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
                 services: list,
                 log_interval: int, detection_interval: int, charting_interval: int):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        ServiceAbstract.__init__(self)
        self.id = id(self)

        self.monitor_name: str = monitor_config.get('monitor_name')
        self.name = f"MonitorServiceThread-{self.monitor_name}"
        self.detector_id = monitor_config.get('detector_id')
        self.detector_name = monitor_config.get('detector_name')
        self.detector_model = monitor_config.get('detector_model')
        self.feed_url = monitor_config.get('feed_url')
        self.feed_id = monitor_config.get('feed_id')

        self.time_zone = monitor_config.get('time_zone')
        self.logging_on = monitor_config.get('logging_on')
        self.notifications_on = monitor_config.get('notifications_on')
        self.charting_on = monitor_config.get('charting_on')
        self.charting_interval: int = charting_interval

        self.services: list = services

        # DETECTOR STATES
        self.running = False
        self.show_full_stream = False
        self.display = False

        # QUEUES
        self.queue_rawframe = queue.Queue(BUFFER_SIZE)
        self.queue_detframe = queue.Queue(BUFFER_SIZE)
        self.queue_detready = queue.Queue(BUFFER_SIZE)
        self.queue_refframe = queue.Queue(BUFFER_SIZE)
        self.queue_dets_not = queue.Queue(BUFFER_SIZE)
        self.queue_dets_log = queue.Queue(BUFFER_SIZE)

        # Monitor Service Parameters
        self.notified_objects: list = monitor_config.get('notified_objects')
        self.log_objects: list = monitor_config.get('log_objects')
        self.log_interval: int = log_interval
        self.log_channel_url: str = '/ws/traffic_monitor/log/'
        self.detection_interval: int = detection_interval

        self.active_services = []

        self.subject_name = f"monitor_service__{self.monitor_name}"

        # set arguments used to start monitor
        self.service_kwargs = {
            'monitor_name': self.monitor_name,
            'time_zone': self.time_zone,
            'detector_id': self.detector_id,
            'detector_name': self.detector_name,
            'detector_model': self.detector_model,
            'queue_detready': self.queue_detready,
            'queue_detframe': self.queue_detframe,
            'queue_dets_log': self.queue_dets_log,
            'queue_dets_mon': self.queue_dets_not,
            'notified_objects': self.notified_objects,
            'log_objects': self.log_objects,
            'log_interval': self.log_interval,
            'detection_interval': self.detection_interval,
            'charting_interval': self.charting_interval
        }

        self.detector = DetectorMachineFactory().get_detector_machine(**self.service_kwargs)

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    @staticmethod
    def _get_message_info(subject_name, subject_info):
        if len(subject_info) == 1:
            return {}  # keyword not found
        elif subject_info[0] == subject_name:
            return subject_info[1]
        else:
            for s in subject_info:
                if type(s) == tuple:
                    return MonitorService._get_message_info(subject_name, s[1])

        return {}

    def update(self, subject_info: tuple):
        """
        Calling update() with a subject_info tuple, will send the tuple of data to
        any observers that are registered with the Monitor.

        :param subject_info:
        :return: None
        """
        logger.info(f"{[{__name__}]} :UPDATED WITH: {subject_info}")
        # messages include the function name and parameter that should be
        # applied to each service that implements the function.

        # get the subject info
        # the result is a k, v entry where the key is a function name
        # and the value is a parameter value to apply to the function
        subject_info: dict = MonitorService._get_message_info('Monitor', subject_info)

        # for each service, apply function with attribute if the function
        # is supported by the service
        try:
            for f_name, a_value in subject_info.items():
                if hasattr(self, f_name) and callable(getattr(self, f_name)):
                    func = getattr(self, f_name)
                    if a_value:
                        rv = func(a_value)
                    else:
                        rv = func()
                    logger.info(f"'{self.__class__.__name__}' :UPDATED WITH: {f_name}({a_value}) RV: {rv}")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}]: {e}")

    def set_objects(self, objects: list, _type: str):
        pass

    def set_log_objects(self, objects: list):
        self.log_objects = objects
        f_name = 'set_log_objects'
        try:
            for s in self.active_services:
                if hasattr(s, f_name) and callable(getattr(s, f_name)):
                    func = getattr(s, f_name)
                    rv = func(objects)
                    logger.info(f"'{s.__class__.__name__}' :UPDATED WITH: {f_name}({objects}) RV: {rv}")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}]: {e}")

    def get_next_frame(self):
        q = self.queue_refframe.get()
        return q.get()

    def start(self) -> dict:
        """
        Overriding Threading.start() so that we can test if a monitor service  is already active for
        the monitor and set the 'running' variable.
        :return: A dict with bool 'success' and string 'message' describing result.
        """
        try:
            self.running = True
            threading.Thread.start(self)
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

        # start the detector machine
        self.detector.start()
        # register monitor_service with detector to get detector updates
        self.detector.register(self)

        # start services and register the monitor as observer of the service
        # active_services = []
        for service in self.services:
            s: ServiceAbstract = service(**self.service_kwargs)
            self.register(s)  # register the service as an observer with the monitor service
            s.start()
            self.active_services.append(s)

        logger.info(f"Starting monitoring service for id: {self.monitor_name}")
        logger.info(f"Monitor Service Running for {self.monitor_name}: {self.running}")
        logger.info(f"Video Capture Opened: {cap.isOpened()}")
        while self.running and cap.isOpened():

            cap.grab()  # only read every other frame
            success, frame = cap.read()

            # if detector is ready, place frame in queue for the
            # detector to pick up, else put in raw frame queue.
            if success:

                # if detector is ready, perform frame detection
                if self.detector.is_ready:
                    try:
                        self.queue_detready.put(frame, block=False)
                        target_queue = self.queue_detframe
                    except queue.Full:
                        continue  # if queue is full skip

                elif self.show_full_stream:  # just use the raw frame from feed without detection
                    try:
                        self.queue_rawframe.put({'frame': frame}, block=False)
                        target_queue = self.queue_rawframe
                    except queue.Full:
                        continue  # if queue is full skip
                else:
                    continue

                # Now, update the reference queue with the type of frame
                if self.display:
                    try:
                        self.queue_refframe.put(target_queue, block=False)
                    except queue.Full:
                        # if q is full, remove next item to make room
                        logger.info("Ref Queue Full!  Making room.")
                        _ = self.get_next_frame()
                        self.queue_refframe.put(target_queue, block=False)

        logger.info(f"[{self.monitor_name}] Stopped monitor service")

        # stop the services
        self.detector.stop()

        for s in self.active_services:
            s: ServiceAbstract = s
            s.stop()
            s.join()

        self.detector.join()

        logger.info(f"[{self.monitor_name}] Monitor Service and its services are all stopped!")

    @staticmethod
    def get_trained_objects(detector_name) -> list:
        return DetectorMachineFactory().get_trained_objects(detector_name)

