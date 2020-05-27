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
from traffic_monitor.models.model_feed import Feed
from traffic_monitor.consumers import ConsumerFactory

BUFFER_SIZE = 256


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

    def __init__(self, detector_id: str, feed_url: str = '1EiC9bvVGnk', feed_timezone: str = 'US/Mountain'):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger('feed_service')
        self.running = False

        self.log_service = None

        # Monitor parameters
        self.detector_id = detector_id
        self.feed_url = feed_url
        self.feed_timezone = feed_timezone
        self.monitor = None

        # QUEUES
        self.rawframe_queue = queue.Queue(BUFFER_SIZE)
        self.detframe_queue = queue.Queue(BUFFER_SIZE)
        self.refframe_queue = queue.Queue(BUFFER_SIZE)

    def __str__(self):
        return "Feed_Service: {} | {} | {}".format(self.detector.name,
                                                   self.detector.model,
                                                   self.feed_url.split('/')[-1])

    def set_monitor(self):
        rv = MonitorFactory().get(detector_id=self.detector_id, feed_id=self.feed)

    def set_detector(self):
        rv = DetectorFactory().get(self.detector_id)
        if not rv['success']:
            raise Exception(rv['message'])

        self.detector = DetectorFactory().get(self.detector_id).get('detector').get('detector')

        self.logger.info(f"Using detector: {self.detector.name}  model: {self.detector.model}")

    def run(self):
        """
        This will start the service by calling threading.Thread.start()
        Frames will be placed in respective queues.
        """
        # set source of video stream
        url, feed_id = Feed.get_stream_url(self.feed_url, self.feed_timezone)
        cap = cv.VideoCapture(url)

        # set the detector
        self.set_detector()

        # get the channel to publish data on
        log_channel = None
        while log_channel is None:
            log_channel = ConsumerFactory.get('/ws/traffic_monitor/log/')

        while cap.isOpened():

            success = False
            while not success:
                success, frame = cap.read()

                # return the frame whether if is directly from feed or with bounding boxes
                frame = cv.imencode('.jpg', frame)[1].tobytes()
                # print(f"yielding frame: {log_interval_timer}")
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
