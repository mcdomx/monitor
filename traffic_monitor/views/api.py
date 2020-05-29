import json
import logging
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from traffic_monitor.views import video_views
from traffic_monitor.models.model_monitor import Monitor
from traffic_monitor.services.monitor_service import MonitorService


logger = logging.getLogger('api')


def get_class_data(request, monitor_id):
    """ Get class data including class_name, class_id, is_mon_on and is_log_on"""

    class_data = video_views.get_class_data(request, monitor_id)
    class_data = {c['class_id']: {'class_name': c['class_name'],
                                  'class_id': c['class_name'].replace(' ', '_'),
                                  'is_monitoring': c['is_monitoring'],
                                  'is_logging': c['is_logging']} for c in class_data}

    return JsonResponse(class_data, safe=False)


def toggle_box(request):
    divid = request.body.decode()
    divid = dict(json.loads(divid))

    action = divid.get('action')
    class_id = divid.get('class_id')
    monitor_id = int(divid.get('monitor_id'))
    print(action, class_id, monitor_id)

    rv = video_views.toggle_box(action, class_id, monitor_id)

    print(rv)

    return HttpResponse(rv)


def toggle_all(request, monitor_id, action):

    logger.info(f"TOGGLE ALL: {action} - {monitor_id}")
    rv = video_views.toggle_all(monitor_id=monitor_id, action=action)

    logger.info(rv)

    return HttpResponse(rv)


def get_active_monitors(request):

    active_monitors = video_views.get_active_monitors()

    rv = {m_id: {'id': m_id,
                 'detector': m.detector.detector_id,
                 'feed': m.feed.description} for m_id, m in active_monitors.items()}

    return JsonResponse(rv, safe=False)


def get_all_monitors(request):

    rv = video_views.get_all_monitors()

    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    all_monitors = rv.get('monitors')
    active_monitors = video_views.get_active_monitors().keys()

    rv = {m.id: {'id': m.id,
                 'is_active': True if m.id in active_monitors else False,
                 'detector': m.detector.detector_id,
                 'feed': m.feed.description} for m in all_monitors}

    return JsonResponse(rv, safe=False)


def start_monitor(request, monitor_id: int):

    # get db details
    rv = Monitor.get(monitor_id)
    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    monitor = rv.get('monitor')
    ms = MonitorService(detector_id=monitor.detector.detector_id, feed_cam=monitor.feed.cam)
    ms.start()

    return JsonResponse({'success': True, 'monitor_id': ms.monitor.id}, safe=False)
