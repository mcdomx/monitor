"""
This is the top level service for a feed.  This service contains
all the information and supporting services that will execute
a feed, display the feed and log its data.
"""

import threading
import queue
import logging

import cv2 as cv

from traffic_monitor.detectors.detector_factory import DetectorFactory
# from traffic_monitor.models.model_monitor import Monitor, MonitorFactory
from traffic_monitor.models.model_feed import FeedFactory
from traffic_monitor.services.log_service import LogService
from traffic_monitor.services.observer import Observer, Subject
from traffic_monitor.services.chart_service import ChartService
from traffic_monitor.services.active_monitors import ActiveMonitors

BUFFER_SIZE = 512

logger = logging.getLogger('monitor_service')


class MonitorService(threading.Thread, Observer, Subject):
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
                 # monitor: Monitor,
                 # logged_objects: list = None, notified_objects: list = None,
                 log_interval: int = 60, detection_interval: int = 5):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        threading.Thread.__init__(self)
        Observer.__init__(self)
        Subject.__init__(self)
        self.id = id(self)
        self.name = f"MonitorServiceThread-{monitor.name}"
        # self.monitor: Monitor = monitor

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
        # self.notified_objects = self.monitor.notification_objects
        # self.logged_objects = self.monitor.log_objects
        self.log_interval: int = log_interval
        self.log_channel_url: str = '/ws/traffic_monitor/log/'
        self.detection_interval: int = detection_interval

        self.subject_name = f"monitor_service__{self.monitor.name}"
        self.detector = self.get_detector()

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    def update(self, subject_info: tuple):
        """
        Calling update() with a subject_info tuple, will send the tuple of data to
        any observers that are registered with the Monitor.

        :param subject_info:
        :return: None
        """

        self.publish(subject_info)

    def get_detector(self):
        """
        Returns a detector instance based on the settings of the service.
        The service object itself cannot be used to instantiate the new class
        as this will cause a circular dependency.

        :return: An instance of Detector.
        """
        rv = DetectorFactory().get(
            detector_id=self.monitor.detector.detector_id,
            queue_detready=self.queue_detready,
            queue_detframe=self.queue_detframe,
            queue_dets_log=self.queue_dets_log,
            queue_dets_not=self.queue_dets_not,
            notified_objects=self.monitor.notification_objects,
            logged_objects=self.monitor.log_objects,
            detection_interval=self.detection_interval
        )
        if rv.get('success'):
            return rv.get('detector')
        else:
            raise Exception(rv.get('message'))

    # @staticmethod
    # def get_feed(feed_cam):
    #     rv = FeedFactory().get(feed_cam)
    #     if rv.get('success'):
    #         return rv.get('feed')
    #     else:
    #         raise Exception(rv.get('message'))
    #
    # @staticmethod
    # def get_monitor(d_id, feed_cam):
    #     rv = MonitorFactory().get(d_id, feed_cam)
    #     if rv.get('success'):
    #         return rv.get('monitor')
    #     else:
    #         raise Exception(rv.get('message'))

    def get_next_frame(self):
        q = self.queue_refframe.get()
        return q.get()

    def start(self) -> dict:
        """
        Overriding Threading.start() so that we can test if a monitor service  is already active for
        the monitor and set the 'running' variable.
        :return: A dict with bool 'success' and string 'message' describing result.
        """
        rv = ActiveMonitors().add(self.monitor.name, self)
        if rv['success']:
            self.running = True
            threading.Thread.start(self)
            return{'success': True, 'message': f"Service started for {self.monitor.name}"}
        else:
            return rv

    def stop(self):
        self.running = False
        ActiveMonitors().remove(self.monitor.name)

    def run(self):
        """
        This will start the service by calling threading.Thread.start()
        Frames will be placed in respective queues.
        """
        # set source of video stream
        cap = cv.VideoCapture(self.monitor.feed.url)

        # start detector instance
        self.detector.start()

        # start a logging service and register as observer
        if self.monitor.logging_on:
            log = LogService(monitor_id=self.monitor.id,
                             queue_dets_log=self.queue_dets_log,
                             log_interval=self.log_interval)
            log.register(self)  # register with the log service to get log updates
            log.start()

        # start a charting service and register as observer
        if self.monitor.charting_on:
            chart = ChartService(monitor_id=self.monitor.id, charting_interval=self.log_interval)
            chart.register(self)
            chart.start()

        # start notification service and register as observer
        if self.monitor.notifications_on:
            """Future release functionality"""
            pass

        logger.info(f"Starting monitoring service for id: {self.monitor.id}")
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
        log.stop()

        self.detector.join()
        log.join()

        logger.info(f"Monitor Service, Detector and Log are stopped!")


