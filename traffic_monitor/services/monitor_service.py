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
from traffic_monitor.models.model_monitor import Monitor, MonitorFactory
from traffic_monitor.models.model_feed import FeedFactory
from traffic_monitor.services.log_service import LogService
from traffic_monitor.services.observer import Observer, Subject
from traffic_monitor.services.chart_service import ChartService

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
    instances = {}

    @classmethod
    def get_instances(cls):
        return cls.instances

    @classmethod
    def get_instance(cls, monitor_id: int):
        return cls.instances.get(monitor_id, None)

    def __init__(self,
                 monitor: Monitor,
                 logged_objects: list = None, notified_objects: list = None,
                 log_interval: int = 60, detection_interval: int = 5):
        """ Requires existing detector and feed """
        threading.Thread.__init__(self)
        Observer.__init__(self)
        Subject.__init__(self)
        self.id = id(self)
        self.name = f"MonitorServiceThread-{monitor.name}"
        self.monitor: Monitor = monitor

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
        self.notified_objects: list = [] if notified_objects is None else notified_objects
        self.logged_objects: list = [] if logged_objects is None else logged_objects
        self.log_interval: int = log_interval
        self.log_channel_url: str = '/ws/traffic_monitor/log/'
        self.detection_interval: int = detection_interval

        # Set monitor objects and classes used
        # detector, detector_class = self.get_detector(detector_id)
        # self.detector: Detector = detector
        # self.detector_class: Detector_Abstract = detector_class

        self.subject_name = f"monitor_service__{self.monitor.name}"
        self.detector = self.get_detector()

        # Setup supported classes in the DB
        # self.load_classes()
        # self.update_monitored_objects()
        # self.update_logged_objects()

        self.__class__.instances.update({self.id: self})

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    def get_logged_objects(self):
        return self.logged_objects

    def get_notified_objects(self):
        return self.notified_objects

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
            notified_objects=self.notified_objects,
            logged_objects=self.logged_objects,
            detection_interval=self.detection_interval
        )
        if rv.get('success'):
            return rv.get('detector')
        else:
            raise Exception(rv.get('message'))

    @staticmethod
    def get_feed(feed_cam):
        rv = FeedFactory().get(feed_cam)
        if rv.get('success'):
            return rv.get('feed')
        else:
            raise Exception(rv.get('message'))

    @staticmethod
    def get_monitor(d_id, feed_cam):
        rv = MonitorFactory().get(d_id, feed_cam)
        if rv.get('success'):
            return rv.get('monitor')
        else:
            raise Exception(rv.get('message'))

    # def load_classes(self):
    #     """ Load supported classes into the DB """
    #     # get the classes that are supported by the detector
    #     classes = self.detector.get_trained_objects()
    #
    #     # create or update the classes
    #     for class_name in classes:
    #         Class.create(class_name=class_name, monitor=self.monitor)
    #
    # def update_monitored_objects(self):
    #     self.monitored_objects = Class.get_notified_objects(self.monitor)
    #     self.detector.set_monitored_objects(self.monitored_objects)
    #
    # def update_logged_objects(self):
    #     self.logged_objects = Class.get_logged_objects(self.monitor)
    #     self.detector.set_logged_objects(self.logged_objects)

    def get_trained_objects(self) -> set:
        """ Retrieves classes supported by detector """
        return self.detector.get_trained_objects()

    def toggle_notified_object(self, object_name) -> dict:
        """
        Toggle a single object's notification status on or off by the name of the object.

        :param object_name: String name of the object
        :return: None if object is not supported and no action taken; else; the name of the object.
        """
        if object_name not in self.get_trained_objects():
            return {"success": False, "message": f"'{object_name}' is not a trained object."}

        if object_name in self.notified_objects:
            self.notified_objects.remove(object_name)
            return {"success": True, "message": f"'{object_name}' removed from notified items."}
        elif object_name in self.get_trained_objects():
            self.notified_objects.append(object_name)
            return {"success": True, "message": f"'{object_name}' added to notified items."}

        return {"success": False, "message": f"Unable to toggle object: '{object_name}'."}

    def toggle_logged_object(self, object_name) -> dict:
        """
        Toggle a single object's logging status on or off by the name of the object.

        :param object_name: String name of the object
        :return: None if object is not supported and no action taken; else; the name of the object.
        """
        if object_name not in self.get_trained_objects():
            return {"success": False, "message": f"'{object_name}' is not a trained object."}

        if object_name in self.logged_objects:
            self.logged_objects.remove(object_name)
            return {"success": True, "message": f"'{object_name}' removed from logged items."}
        elif object_name in self.get_trained_objects():
            self.logged_objects.append(object_name)
            return {"success": True, "message": f"'{object_name}' added to logged items."}

        return {"success": False, "message": f"Unable to toggle object: '{object_name}'."}

    def toggle_all_notifications(self):
        """
        Invert the list of notified objects
        :return: The new set of notified objects
        """
        self.notified_objects = self.get_trained_objects() - self.notified_objects
        return self.notified_objects

        # rv = Class.toggle_all_notifications(self.monitor)
        # self.update_monitored_objects()
        # return rv

    def toggle_all_log(self):
        """
        Invert the list of logged objects
        :return: The new set of logged objects
        """
        self.logged_objects = self.get_trained_objects() - self.logged_objects
        return self.logged_objects

        # rv = Class.toggle_all_log(self.monitor)
        # self.update_logged_objects()
        # return rv

    def get_next_frame(self):
        q = self.queue_refframe.get()
        return q.get()

    def start(self):
        self.running = True
        threading.Thread.start(self)
        ActiveMonitorServices().add(self)

    def stop(self):
        self.running = False
        ActiveMonitorServices().remove(self)

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
        log = LogService(monitor_id=self.monitor.id,
                         queue_dets_log=self.queue_dets_log,
                         log_interval=self.log_interval)
        log.register(self)  # register with the log service to get log updates
        log.start()

        # start a charting service and register as observer
        chart = ChartService(monitor_id=self.monitor.id, charting_interval=self.log_interval)
        chart.register(self)
        chart.start()

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


class ActiveMonitorServices:
    singelton = None

    def __new__(cls):
        if cls.singelton is None:
            cls.singelton = cls._Singleton()
        return cls.singelton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('detector')
            self.active_monitors = {}
            self.viewing_monitor: MonitorService = None

        def add(self, monitor_service: MonitorService):
            self.active_monitors.update({monitor_service.id: monitor_service})

        def view(self, monitor_id: int):
            ms = self.active_monitors.get(monitor_id)
            if ms is None:
                return {'success': False, 'message': f"MonitorService with is '{monitor_id}' is not active."}

            # if any monitor is currently being viewed, turn it off
            if self.viewing_monitor:
                self.viewing_monitor.display = False

            # set the viewing monitor and set viewing to true
            self.viewing_monitor: MonitorService = ms
            self.viewing_monitor.display = True

            return {'success': True, 'monitor_service': ms}

        def remove(self, monitor_service: MonitorService):
            # if removing a monitor that is being viewed stop it
            if self.viewing_monitor:
                if self.viewing_monitor is monitor_service:
                    self.viewing_monitor.display = False
                    self.viewing_monitor = None

            self.active_monitors.pop(monitor_service.monitor.id)

        def get(self, monitor_id: int):
            ms = self.active_monitors.get(monitor_id)

            if ms is None:
                return {'success': False, 'message': f"MonitorService with is '{monitor_id}' is not active."}

            return {'success': True, 'monitor_service': ms}

        def getall(self):
            return self.active_monitors
