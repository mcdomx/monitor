"""
This is the top level service for a feed.  This service contains
all the information and supporting services that will execute
a feed, display the feed and log its data.
"""

import threading

from traffic_monitor.detectors.detector_factory import *
from traffic_monitor.detectors.detector_abstract import Detector_Abstract
from traffic_monitor.models.model_monitor import *
from traffic_monitor.models.model_feed import *
from traffic_monitor.models.model_class import Class
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
    return detection frames when it is able to.  When running,
    The feed service will place frames in a queue.
    If the frame includes detections, it will also put the
    detections in the frame.  If the application is set to
    display the feed from the Monitor, the application can
    get the images to display from the queue of images.
    """

    def __init__(self, detector_id: str, feed_cam: str, log_interval: int = 60, detection_interval: int = 5):
        """ Requires existing detector and feed """
        threading.Thread.__init__(self)
        Observer.__init__(self)
        Subject.__init__(self)
        self.name = "Monitor_Service_Thread"

        # DETECTOR STATES
        self.running = False
        self.show_full_stream = False
        self.display = False

        # QUEUES
        self.queue_rawframe = queue.Queue(BUFFER_SIZE)
        self.queue_detframe = queue.Queue(BUFFER_SIZE)
        self.queue_detready = queue.Queue(BUFFER_SIZE)
        self.queue_refframe = queue.Queue(BUFFER_SIZE)
        self.queue_dets_mon = queue.Queue(BUFFER_SIZE)
        self.queue_dets_log = queue.Queue(BUFFER_SIZE)

        # Monitor parameters
        self.monitored_objects = None
        self.logged_objects = None
        self.log_interval = log_interval
        self.log_channel_url = '/ws/traffic_monitor/log/'
        self.detection_interval = detection_interval

        # Set monitor objects and classes used
        detector, detector_class = self.get_detector(detector_id)
        self.detector: Detector = detector
        self.detector_class: Detector_Abstract = detector_class
        self.feed: Feed = self.get_feed(feed_cam)
        self.monitor: Monitor = self.get_monitor(detector_id, feed_cam)
        self.subject_name = f"monitor_service__{self.monitor.id}"

        # Setup supported classes in the DB
        self.load_classes()
        self.update_monitored_objects()
        self.update_logged_objects()

    def __str__(self):
        return "Monitor_Service: {} | {} | {}".format(self.detector.name,
                                                      self.detector.model,
                                                      self.feed.cam.split('/')[-1])

    def update(self, subject_info: tuple):
        """ Handle updates from Subjects. Republish info received from subject. """
        self.publish(subject_info)

    def get_detector(self, d_id):
        rv = DetectorFactory().get(detector_id=d_id,
                                   queue_detready=self.queue_detready,
                                   queue_detframe=self.queue_detframe,
                                   queue_dets_log=self.queue_dets_log,
                                   queue_dets_mon=self.queue_dets_mon,
                                   mon_objs=self.monitored_objects,
                                   log_objs=self.logged_objects,
                                   detection_interval=self.detection_interval)
        if rv.get('success'):
            return rv.get('detector'), rv.get('class')
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

    def load_classes(self):
        """ Load supported classes into the DB """
        # get the classes that are supported by the detector
        classes = self.detector_class.get_trained_objects()

        # create or update the classes
        for class_name in classes:
            Class.create(class_name=class_name, monitor=self.monitor)

    def update_monitored_objects(self):
        self.monitored_objects = Class.get_monitored_objects(self.monitor)
        self.detector_class.set_monitored_objects(self.monitored_objects)

    def update_logged_objects(self):
        self.logged_objects = Class.get_logged_objects(self.monitor)
        self.detector_class.set_logged_objects(self.logged_objects)

    def get_class_data(self):
        """ Retrieves classes supported by detector """
        return self.detector_class.get_class_data(self.monitor.id)

    def toggle_monitor(self, class_id):
        rv = Class.toggle_mon(class_id=class_id, monitor=self.monitor)
        self.update_monitored_objects()
        return rv

    def toggle_log(self, class_id):
        rv = Class.toggle_log(class_id=class_id, monitor=self.monitor)
        self.update_logged_objects()
        return rv

    def toggle_all_mon(self):
        rv = Class.toggle_all_mon(self.monitor)
        self.update_monitored_objects()
        return rv

    def toggle_all_log(self):
        rv = Class.toggle_all_log(self.monitor)
        self.update_logged_objects()
        return rv

    def get_next_frame(self):
        q = self.queue_refframe.get()
        return q.get()

    def start(self):
        self.running = True
        threading.Thread.start(self)
        ActiveMonitors().add(self)

    def stop(self):
        self.running = False
        ActiveMonitors().remove(self)

    def run(self):
        """
        This will start the service by calling threading.Thread.start()
        Frames will be placed in respective queues.
        """
        # set source of video stream
        cap = cv.VideoCapture(self.feed.url)

        # start detector instance
        det = self.detector_class
        det.start()

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

                if det.is_ready:
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
        det.stop()
        log.stop()

        det.join()
        log.join()

        logger.info(f"Monitor Service, Detector and Log are stopped!")


class ActiveMonitors:
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
            self.active_monitors.update({monitor_service.monitor.id: monitor_service})

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
