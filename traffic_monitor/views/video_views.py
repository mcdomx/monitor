import logging

import cv2

from django.http import StreamingHttpResponse

from traffic_monitor.services.monitor_service import MonitorService
from traffic_monitor.services.monitor_service_manager import MonitorServiceManager
from traffic_monitor.websocket_channels_factory import ChannelFactory

from traffic_monitor.services.observer import Observer

logger = logging.getLogger('view')


class Publisher(Observer):

    def __init__(self, subject_name: str, monitor_id: int, channel_url: str):
        Observer.__init__(self)
        self.monitor_id = monitor_id
        self.channel_url = channel_url
        self.subject_name = subject_name

    def update(self, subject_info: tuple):
        subject_name, context = subject_info

        while type(context) is tuple:
            subject_name, context = context

        subject_name, monitor_id = subject_name.split('__')

        if subject_name == self.subject_name:
            # get the channel to publish log data on
            channel = None
            while channel is None:
                channel = ChannelFactory.get(self.channel_url)
            channel.update(context)


# VIDEO STREAM FUNCTIONS
def gen_stream(monitor_id: int):
    """Video streaming generator function."""

    # rv = ActiveMonitors().get(monitor_id)
    rv = MonitorServiceManager().view(monitor_id)  # gets monitor and turn on viewing mode
    ms: MonitorService = rv.get('monitor_service')

    if ms is None:
        logger.error(f"Monitor ID: '{monitor_id}' is not active.")
        return

    # Register a log publisher with the monitor service so that
    # messages with 'logservice' are updated in the page's detection log
    ms.register(Publisher('logservice', monitor_id, '/ws/traffic_monitor/log/'))
    ms.register(Publisher('chartservice', monitor_id, '/ws/traffic_monitor/chart/'))

    while ms.display:

        rv = ms.get_next_frame()
        frame = rv.get('frame')

        # return the frame whether if is directly from feed or with bounding boxes
        frame = cv2.imencode('.jpg', frame)[1].tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


def video_feed(request, monitor_id: int):
    """Video streaming route. Put this in the src attribute of an img tag."""

    return StreamingHttpResponse(gen_stream(monitor_id), content_type="multipart/x-mixed-replace;boundary=frame")


# def get_class_data(request, monitor_id):
#     """ Get class data including class_name, class_id, is_mon_on and is_log_on"""
#     return Class.objects.filter(monitor_id=monitor_id).values()


def toggle_box(action: str, class_id: str, monitor_id: int):
    rv = MonitorServiceManager().get(monitor_id)
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
    rv = MonitorServiceManager().get(monitor_id)
    if not rv['success']:
        logger.error(f"No active monitor with id: {monitor_id}")
        logger.error(f"Active monitors: \n {[x for x in MonitorServiceManager().getall()]}")
    ms: MonitorService = rv.get('monitor_service')

    if action == 'mon':
        rv = ms.toggle_all_mon()
    elif action == 'log':
        rv = ms.toggle_all_log()
    else:
        return {'success': False, 'message': f"ERROR: can only toggle mon or log, not {action}"}

    return rv



# END VIDEO STEAMING FUNCTIONS ##########################
