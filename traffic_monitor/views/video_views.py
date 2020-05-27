import logging
import time

import pafy
import cv2
import numpy as np
import datetime
import pytz

from django.http import StreamingHttpResponse

from traffic_monitor.detectors.detector_factory import DetectorFactory
from traffic_monitor.models.model_feed import Feed
from traffic_monitor.models.model_logentry import LogEntry
from traffic_monitor.consumers import ConsumerFactory

from .elapsed_time import ElapsedTime

logger = logging.getLogger('view')


# VIDEO STREAM FUNCTIONS
def gen_stream(detector_id):
    """Video streaming generator function."""

    # set source of video stream
    cam_stream = '1EiC9bvVGnk'
    cam_stream_timezone = 'US/Mountain'
    url, feed_id = Feed.get_stream_url(cam_stream, cam_stream_timezone)
    cap = cv2.VideoCapture(url)

    # set the detector to use (supports: yolov3, yolov3-tiny)
    rv = DetectorFactory().get(detector_id)
    if not rv['success']:
        return rv['message']

    detector = rv.get('detector').get('detector')
    logger.info(f"Using detector: {detector.name}  model: {detector.model}")

    # get the channel to publish data on
    log_channel = None
    while log_channel is None:
        log_channel = ConsumerFactory.get('/ws/traffic_monitor/log/')

    log_interval = 60  # frequency in seconds which avg detections per minute are calculated
    capture_interval = 5  # freq in seconds which objects are counted
    display_interval = 1  # freq in seconds which objects are displayed (<= capture_interval)
    capture_count = 0
    log_interval_detections = []
    capture_interval_timer = ElapsedTime()
    log_interval_timer = ElapsedTime()
    display_interval_timer = ElapsedTime(adj=-1 * display_interval)

    while True:

        # sleep_time = max(0, capture_interval - (datetime.datetime.now() - start_time).seconds)
        # time.sleep(sleep_time)
        # print(f"start loop: {log_interval_timer}")
        #
        # print(f"MSEC {cap.get(cv2.CAP_PROP_POS_MSEC)}")
        # print(f"FRMES {cap.get(cv2.CAP_PROP_POS_FRAMES)}")
        # print(f"RATIO {cap.get(cv2.CAP_PROP_POS_AVI_RATIO)}")
        # print(f"BUF SIZE {cap.get(cv2.CAP_PROP_BUFFERSIZE)}")

        frame = None
        while display_interval_timer.get() < display_interval:
            # cap.open(url)
            _ = cap.grab()
            # logger.info(f"grabbed frame: {log_interval_timer} {display_interval - display_interval_timer.get()}")

        success = False
        while not success:
            success, frame = cap.read()
        display_interval_timer.reset()
        # print(f"read frame: {log_interval_timer}")

        # if time elapsed dictates capturing objects, perform capture
        if capture_interval_timer.get() >= capture_interval:
            # print(f"capture start: {log_interval_timer}")
            _, frame, frame_detections, mon_detections = detector.detect(frame)
            log_interval_detections += frame_detections
            capture_count += 1
            capture_interval_timer.reset()

            log_text = f"{log_interval_timer}/{capture_count}: {frame_detections}"
            print(f"{' ':50}", end='\r')
            print(log_text, end='\r')

        # if log interval reached, record average items per minute
        if log_interval_timer.get() >= log_interval:
            # print(f"start logging: {log_interval_timer}")
            # tally list
            objs_unique = set(log_interval_detections)
            # Counts the mean observation count at any moment over the log interval period.
            minute_counts_dict = {obj: round(log_interval_detections.count(obj) / capture_count, 3) for obj in
                                  objs_unique}
            timestamp = datetime.datetime.now(tz=pytz.timezone(cam_stream_timezone))
            LogEntry.add(time_stamp=timestamp,
                         detector_id=detector_id,
                         feed_id=feed_id,
                         count_dict=minute_counts_dict)

            logger.info(minute_counts_dict)
            log_channel.update({'timestamp': timestamp, 'counts': minute_counts_dict})

            # restart the log interval counter, clear the detections and restart the capture count
            log_interval_timer.reset()
            log_interval_detections.clear()
            capture_count = 0
            # print(f"end logging: {log_interval_timer}")

        # return the frame whether if is directly from feed or with bounding boxes
        frame = cv2.imencode('.jpg', frame)[1].tobytes()
        # print(f"yielding frame: {log_interval_timer}")
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


def video_feed(request, detector_id):
    """Video streaming route. Put this in the src attribute of an img tag."""

    return StreamingHttpResponse(gen_stream(detector_id), content_type="multipart/x-mixed-replace;boundary=frame")


def get_class_data(detector_id):
    """ Get class data including class_name, class_id, is_mon_on and is_log_on"""
    d = DetectorFactory().get(detector_id).get('detector').get('detector')
    class_data = d.get_class_data(detector_id)

    return class_data


def toggle_box(action: str, class_id: str, detector_id: str):
    d = DetectorFactory().get(detector_id).get('detector').get('detector')
    if action == 'mon':
        rv = d.toggle_monitor(class_id)
    elif action == 'log':
        rv = d.toggle_log(class_id)
    else:
        return {'success': False, 'message': f"ERROR: can only toggle 'mon' or 'log', not '{action}'"}

    return rv


def toggle_all(detector_id: str, action: str):
    d = DetectorFactory().get(detector_id).get('detector').get('detector')
    if action == 'mon':
        rv = d.toggle_all_mon()
    elif action == 'log':
        rv = d.toggle_all_log()
    else:
        return {'success': False, 'message': f"ERROR: can only toggle mon or log, not {action}"}

    return rv

# END VIDEO STEAMING FUNCTIONS ##########################
