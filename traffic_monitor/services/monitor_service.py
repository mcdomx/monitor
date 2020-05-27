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
from traffic_monitor.models.model_monitor import MonitorFactory
from traffic_monitor.models.model_feed import FeedFactory
from traffic_monitor.consumers import ConsumerFactory

BUFFER_SIZE = 256

logger = logging.getLogger('monitor_service')


class MonitorService(threading.Thread):
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

    def __init__(self, detector_id: str, feed_cam: str):
        """ Requires existing detector and feed """
        threading.Thread.__init__(self)
        self.name = "Monitor_Service_Thread"
        self.running = False

        self.log_service = None

        # QUEUES
        self.queue_rawframe = queue.Queue(BUFFER_SIZE)
        self.queue_detframe = queue.Queue(BUFFER_SIZE)
        self.queue_detready = queue.Queue(5)
        self.queue_refframe = queue.Queue(BUFFER_SIZE)

        # Monitor parameters
        self.detector, self.detector_class = self.get_detector(detector_id, self.queue_detready, self.queue_detframe)
        self.feed = self.get_feed(feed_cam)
        self.monitor = self.get_monitor(detector_id, feed_cam)

    @staticmethod
    def get_detector(d_id, queue_detready, queue_detframe):
        rv = DetectorFactory().get(d_id, queue_detready, queue_detframe)
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

    def __str__(self):
        return "Feed_Service: {} | {} | {}".format(self.detector.name,
                                                   self.detector.model,
                                                   self.feed.cam.split('/')[-1])

    def get_next_frame(self):
        q = self.queue_refframe.get()
        return q.get()

    def start(self):
        self.running = True
        threading.Thread.start(self)

    def stop(self):
        logger.info("Stopping monitor service .. ")
        self.detector_class.stop()
        self.running = False

    def run(self):
        """
        This will start the service by calling threading.Thread.start()
        Frames will be placed in respective queues.
        """
        # set source of video stream
        cap = cv.VideoCapture(self.feed.url)

        # create detector instance
        det = self.detector_class
        det.start()

        # get the channel to publish data on
        # log_channel = None
        # while log_channel is None:
        #     log_channel = ConsumerFactory.get('/ws/traffic_monitor/log/')

        logger.info("Starting monitoring service ... ")
        while self.running and cap.isOpened():

            success, frame = cap.read()

            # if detector is ready, place frame in queue
            # for detector to pick up, else put in raw frame queue.
            if success:
                if det.is_ready:
                    try:
                        self.queue_detready.put(frame, block=False)
                        target_queue = self.queue_detframe
                    except queue.Full:
                        # if queue is full skip
                        continue

                else:
                    # put in raw frame queue
                    try:
                        self.queue_rawframe.put(frame, block=False)
                        target_queue = self.queue_rawframe
                    except queue.Full:
                        # if queue is full skip
                        continue

                # update the reference queue
                try:
                    self.queue_refframe.put(target_queue, block=False)
                except queue.Full:
                    # if q is full, remove next item to make room and then put
                    _ = self.get_next_frame()
                    self.queue_refframe.put(target_queue, block=False)

                # # return the frame whether if is directly from feed or with bounding boxes
                # frame = cv.imencode('.jpg', frame)[1].tobytes()
                # yield (b'--frame\r\n'
                #        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

        logger.info("Stopping detector .. ")
        det.stop()
