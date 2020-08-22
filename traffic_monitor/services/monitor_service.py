"""
This is the top level service for a feed.  This service contains
all the information and supporting services that will execute
a feed, display the feed and log its data.
"""

import threading
import queue
import logging

import cv2 as cv

from traffic_monitor.services.log_service import LogService
from traffic_monitor.services.observer import Observer, Subject
from traffic_monitor.services.chart_service import ChartService
from traffic_monitor.detector_machines.detector_machine_abstract import DetectorMachineAbstract
from traffic_monitor.detector_machines.detetor_machine_factory import DetectorMachineFactory

BUFFER_SIZE = 512

logger = logging.getLogger('monitor_service')

# keeps track of active monitors
active_monitors = {}


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
                 monitor_config: dict,
                 log_interval: int, detection_interval: int):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        threading.Thread.__init__(self)
        Observer.__init__(self)
        Subject.__init__(self)
        self.id = id(self)

        # logger.info(monitor_config)
        self.monitor_name: str = monitor_config.get('monitor_name')
        self.name = f"MonitorServiceThread-{self.monitor_name}"
        self.detector_id = monitor_config.get('detector_id')
        self.detector_name = monitor_config.get('detector_name')
        self.detector_model = monitor_config.get('detector_model')
        self.feed_url = monitor_config.get('feed_url')

        self.time_zone = monitor_config.get('time_zone')
        self.logging_on = monitor_config.get('logging_on')
        self.notifications_on = monitor_config.get('notifications_on')
        self.charting_on = monitor_config.get('charting_on')

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
        kwargs = {
            'detector_id': self.detector_id,
            'detector_name': self.detector_name,
            'detector_model': self.detector_model,
            'queue_detready': self.queue_detready,
            'queue_detframe': self.queue_detframe,
            'queue_dets_log': self.queue_dets_log,
            'queue_dets_mon': self.queue_dets_not,
            'notified_objects': self.notified_objects,
            'logged_objects': self.logged_objects,
            'detection_interval': self.detection_interval
        }

        self.detector = DetectorMachineFactory().get_detector_machine(**kwargs)

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

    def get_next_frame(self):
        q = self.queue_refframe.get()
        return q.get()

    @staticmethod
    def start_monitor(monitor_config: dict, log_interval: int, detection_interval: int) -> dict:
        """
        Setup and start a monitoring service with respective support services for logging, notifying and charting.

        :param monitor_config: Monitor configuration dictionary
        :param detection_interval:
        :param log_interval:
        :return: Dictionary with 'success' bool and 'message' indicating result
        """

        # check if the monitor is already active
        if MonitorService.is_active(monitor_config.get('monitor_name')):
            return {'success': False, 'message': f"Service for monitor '{monitor_config.get('monitor_name')}' is already active."}

        ms = MonitorService(monitor_config=monitor_config,
                            log_interval=log_interval,
                            detection_interval=detection_interval)

        rv = ms.start()
        return rv

    @staticmethod
    def stop_monitor(monitor_name) -> dict:
        # check if the monitor is already active
        if not MonitorService.is_active(monitor_name):
            return {'success': False,
                    'message': f"Service for monitor '{monitor_name}' is not active."}
        ms = active_monitors.get(monitor_name)
        ms.running = False
        del active_monitors[monitor_name]
        return {'success': True, 'message': f"Service stopped for {monitor_name}"}

    def start(self) -> dict:
        """
        Overriding Threading.start() so that we can test if a monitor service  is already active for
        the monitor and set the 'running' variable.
        :return: A dict with bool 'success' and string 'message' describing result.
        """
        self.running = True
        threading.Thread.start(self)
        active_monitors.update({self.monitor_name: self})
        return{'success': True, 'message': f"Service started for {self.monitor_name}"}

    def run(self):
        """
        This will start the service by calling threading.Thread.start()
        Frames will be placed in respective queues.
        """
        # set source of video stream
        cap = cv.VideoCapture(self.feed_url)
        logger.info(cap.isOpened())

        # start the detector machine
        self.detector.start()

        # start a logging service and register as observer
        if self.logging_on:
            log = LogService(monitor_name=self.monitor_name,
                             queue_dets_log=self.queue_dets_log,
                             log_interval=self.log_interval,
                             time_zone=self.time_zone)
            log.register(self)  # register with the log service to get log updates
            log.start()

        # start a charting service and register as observer
        if self.charting_on:
            chart = ChartService(monitor_name=self.monitor_name, charting_interval=self.log_interval)
            chart.register(self)
            chart.start()

        # start notification service and register as observer
        if self.notifications_on:
            """Future release functionality"""
            pass

        logger.info(f"Starting monitoring service for id: {self.monitor_name}")
        logger.info(self.running)
        logger.info(cap.isOpened())
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
        if self.logging_on:
            log.stop()
            log.join()

        if self.charting_on:
            chart.stop()
            chart.join()



        self.detector.join()

        logger.info(f"Monitor Service, Detector and Log are stopped!")

    @staticmethod
    def is_active(monitor_name: str) -> bool:
        if monitor_name in active_monitors.keys():
            return True

        return False

    @staticmethod
    def get_trained_objects(detector_name):
        try:
            objects = DetectorMachineFactory().get_trained_objects(detector_name)
            return {'success': True, 'message': "Trained objects successfully retrieved.", 'objects': objects}
        except Exception as e:
            return {'success': False, 'message': f"Unable to retrieve trained objects: {e}"}



