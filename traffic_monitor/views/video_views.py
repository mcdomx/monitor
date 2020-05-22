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
from traffic_monitor.models.model_log import Log

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

    interval = 1
    capture_interval = 6
    count = 0
    minute_counter = datetime.datetime.now()
    start_time = datetime.datetime.now() - datetime.timedelta(seconds=6)
    while True:

        if (datetime.datetime.now() - start_time).seconds < capture_interval:
            print(f"Sleeping: {capture_interval-(datetime.datetime.now() - start_time).seconds} s")
            time.sleep(capture_interval-(datetime.datetime.now() - start_time).seconds)

        start_time = datetime.datetime.now()

        cap.open(url)
        success, frame = cap.read()

        if not success:
            continue

        count += 1

        minute_detections = []
        if count % interval == 0:
            _, frame, log_detections, mon_detections = detector.detect(frame)
            minute_detections += log_detections
            print(f"{(datetime.datetime.now() - minute_counter).seconds}: {log_detections}", end='\r')
            count = 0
            if (datetime.datetime.now() - minute_counter).seconds >= 60:
                # tally list
                objs_unique = set(minute_detections)
                minute_counts_dict = {obj: minute_detections.count(obj) for obj in objs_unique}
                Log.add(time_stamp=datetime.datetime.now(tz=pytz.timezone(cam_stream_timezone)),
                        detector_id=detector_id,
                        feed_id=feed_id,
                        count_dict=minute_counts_dict)
                logger.info(minute_counts_dict)

                minute_counter = datetime.datetime.now()
                minute_detections.clear()

        frame = cv2.imencode('.jpg', frame)[1].tobytes()

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
