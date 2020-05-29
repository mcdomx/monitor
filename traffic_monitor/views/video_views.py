import logging
import time

import pafy
import cv2
import numpy as np
import datetime
import pytz

from django.http import StreamingHttpResponse

from traffic_monitor.services.monitor_service import MonitorService, ActiveMonitors
from traffic_monitor.detectors.detector_factory import DetectorFactory
from traffic_monitor.models.model_feed import Feed, FeedFactory
from traffic_monitor.models.model_class import Class
from traffic_monitor.models.model_logentry import LogEntry
from traffic_monitor.consumers import ConsumerFactory
from traffic_monitor.models.model_monitor import MonitorFactory

from .elapsed_time import ElapsedTime

logger = logging.getLogger('view')


# VIDEO STREAM FUNCTIONS
def gen_stream(monitor_id: int):
    """Video streaming generator function."""

    rv = ActiveMonitors().get(monitor_id)
    ms: MonitorService = rv.get('monitor_service')
    if ms is None:
        logger.error(f"Monitor ID: '{monitor_id}' does not exist")
        return

    # get the channel to publish data on
    log_channel = None
    while log_channel is None:
        log_channel = ConsumerFactory.get('/ws/traffic_monitor/log/')

    log_interval = 10  # frequency in seconds which avg detections per minute are calculated
    capture_count = 0
    log_interval_detections = []
    log_interval_timer = ElapsedTime()

    while ms.running:

        rv = ms.get_next_frame()
        frame = rv.get('frame')

        # if frame has detections, accumulate them
        detections = rv.get('detections')
        if detections is not None:
            log_interval_detections += detections.get('log')
            capture_count += 1

        # if log interval reached, record average items per minute
        if log_interval_timer.get() >= log_interval:
            # count detections over interval period
            objs_unique = set(log_interval_detections)
            # Counts the mean observation count at any moment over the log interval period.
            minute_counts_dict = {obj: round(log_interval_detections.count(obj) / capture_count, 3) for obj in
                                  objs_unique}
            timestamp = datetime.datetime.now(tz=pytz.timezone(ms.feed.time_zone))
            LogEntry.add(time_stamp=timestamp,
                         monitor_id=ms.monitor.id,
                         count_dict=minute_counts_dict)

            logger.info(f"Internal Detections: {minute_counts_dict}")
            log_channel.update({'timestamp': timestamp, 'counts': minute_counts_dict})

            # restart the log interval counter, clear the detections and restart the capture count
            log_interval_timer.reset()
            log_interval_detections.clear()
            capture_count = 0

        # return the frame whether if is directly from feed or with bounding boxes
        frame = cv2.imencode('.jpg', frame)[1].tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


def video_feed(request, monitor_id: int):
    """Video streaming route. Put this in the src attribute of an img tag."""

    return StreamingHttpResponse(gen_stream(monitor_id), content_type="multipart/x-mixed-replace;boundary=frame")


def get_class_data(request, monitor_id):
    """ Get class data including class_name, class_id, is_mon_on and is_log_on"""
    return Class.objects.filter(monitor_id=monitor_id).values()


def toggle_box(action: str, class_id: str, monitor_id: int):
    rv = ActiveMonitors().get(monitor_id)
    if not rv['success']:
        logger.error(f"No active monitor with id: {monitor_id}")
    ms = rv.get('monitor_service')

    if action == 'mon':
        rv = ms.toggle_monitor(class_id)
    elif action == 'log':
        rv = ms.toggle_log(class_id)
    else:
        return {'success': False, 'message': f"ERROR: can only toggle 'mon' or 'log', not '{action}'"}

    return rv


def toggle_all(monitor_id: int, action: str):
    rv = ActiveMonitors().get(monitor_id)
    if not rv['success']:
        logger.error(f"No active monitor with id: {monitor_id}")
        logger.error(f"Active monitors: \n {[x for x in ActiveMonitors().getall()]}")
    ms: MonitorService = rv.get('monitor_service')

    if action == 'mon':
        rv = ms.toggle_all_mon()
    elif action == 'log':
        rv = ms.toggle_all_log()
    else:
        return {'success': False, 'message': f"ERROR: can only toggle mon or log, not {action}"}

    return rv


def get_active_monitors():
    return ActiveMonitors().getall()


def get_all_monitors():
    return MonitorFactory().getall()


# END VIDEO STEAMING FUNCTIONS ##########################
