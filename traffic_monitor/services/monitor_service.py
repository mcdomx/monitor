"""
This is the top level service for a feed.  This service contains
all the information and supporting services that will execute
a feed, display the feed and log its data.
"""

import threading
import queue
import logging

import cv2 as cv

# from traffic_monitor.services.observer import Observer, Subject
from traffic_monitor.detector_machines.detetor_machine_factory import DetectorMachineFactory
from traffic_monitor.services.service_abstract import ServiceAbstract

BUFFER_SIZE = 512

logger = logging.getLogger('monitor_service')


# class MonitorService(threading.Thread, Observer, Subject):
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
        # threading.Thread.__init__(self)
        # Observer.__init__(self)
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
        self.logged_objects: list = monitor_config.get('logged_objects')
        self.log_interval: int = log_interval
        self.log_channel_url: str = '/ws/traffic_monitor/log/'
        self.detection_interval: int = detection_interval

        self.subject_name = f"monitor_service__{self.monitor_name}"

        # start detector machine
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
            'logged_objects': self.logged_objects,
            'log_interval': self.log_interval,
            'detection_interval': self.detection_interval,
            'charting_interval': self.charting_interval
        }

        self.detector = DetectorMachineFactory().get_detector_machine(**self.service_kwargs)

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    def get_config(self) -> dict:
        config_dict = {
            'thread_name': self.name,
            'monitor_name': self.monitor_name,
            'detector_name': self.detector_name,
            'detector_model': self.detector_model,
            'feed_id': self.feed_id,
            'logging': self.logging_on,
            'logged_objects': self.logged_objects,
            'notifications': self.notifications_on,
            'notified_objects': self.notified_objects,
            'charting': self.charting_on,
            'services': [f"{s.__name__}" for s in self.services]
        }

        return config_dict

    def update(self, subject_info: tuple):
        """
        Calling update() with a subject_info tuple, will send the tuple of data to
        any observers that are registered with the Monitor.

        :param subject_info:
        :return: None
        """
        logger.info(f"{[{__name__}]} :UPDATED WITH: {subject_info}")
        self.publish(subject_info)

    def get_next_frame(self):
        q = self.queue_refframe.get()
        return q.get()

    def start(self) -> str:
        """
        Overriding Threading.start() so that we can test if a monitor service  is already active for
        the monitor and set the 'running' variable.
        :return: A dict with bool 'success' and string 'message' describing result.
        """
        try:
            self.running = True
            threading.Thread.start(self)
            return f"[{__name__}] Service started for:  {self.monitor_name}"
        except Exception as e:
            raise Exception(f"[{__name__}] Could not start '{self.monitor_name}': {e}")

    def stop(self):
        self.running = False

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

        # start services and register the monitor as observer of the service
        active_services = []
        for service in self.services:
            s: ServiceAbstract = service(**self.service_kwargs)
            self.register(s)  # register the service as an observer with the monitor service
            s.start()
            active_services.append(s)

        # # start a logging service and register as observer
        # if self.logging_on:
        #     log = LogService(monitor_name=self.monitor_name,
        #                      queue_dets_log=self.queue_dets_log,
        #                      log_interval=self.log_interval,
        #                      time_zone=self.time_zone)
        #     log.register(self)  # register with the log service to get log updates
        #     log.start()
        #
        # # start a charting service and register as observer
        # if self.charting_on:
        #     chart = ChartService(monitor_name=self.monitor_name,
        #                          charting_interval=self.log_interval)
        #     chart.register(self)
        #     chart.start()

        # # start notification service and register as observer
        # if self.notifications_on:
        #     """Future release functionality"""
        #     pass

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

        logger.info("Stopped monitor service")

        # stop the services
        self.detector.stop()

        for s in active_services:
            s: ServiceAbstract = s
            s.stop()
            s.join()

        # if self.logging_on:
        #     log.stop()
        #     log.join()
        #
        # if self.charting_on:
        #     chart.stop()
        #     chart.join()

        self.detector.join()

        logger.info(f"Monitor Service, Detector and Log are stopped!")


    @staticmethod
    def get_trained_objects(detector_name) -> list:
        return DetectorMachineFactory().get_trained_objects(detector_name)

