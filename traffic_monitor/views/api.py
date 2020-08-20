import json
import logging
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from traffic_monitor.views import video_views, chart_views
from traffic_monitor.models.model_monitor import Monitor, MonitorFactory
from traffic_monitor.models.model_feed import FeedFactory
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.services.monitor_service import MonitorService
from traffic_monitor.services.active_monitors import ActiveMonitors

logger = logging.getLogger('api')


def get_class_data(request, monitor_id):
    """
    Get class data including class_name, class_id, is_mon_on and is_log_on

    :param request:
    :param monitor_id:
    :return:
    """

    class_data = video_views.get_class_data(request, monitor_id)
    class_data = {c['class_id']: {'class_name': c['class_name'],
                                  'class_id': c['class_name'].replace(' ', '_'),
                                  'is_monitoring': c['is_monitoring'],
                                  'is_logging': c['is_logging']} for c in class_data}

    return JsonResponse(class_data, safe=False)


def toggle_box(request):
    """

    :param request:
    :return:
    """

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


def get_streams(request):
    """
    Return a dictionary of all available video streams.

    :param request:  HTML Request. (not used for this function)
    :return: A JsonResponse dictionary of video streams. {stream: {'cam': , 'time_zone': , 'url': ,'description': }}
    """

    rv = FeedFactory().getall()

    if not rv['success']:
        return JsonResponse(rv, safe=False)

    rv = {s['cam']: s for s in rv.get('feeds').values()}

    return JsonResponse(rv, safe=False)


def get_detectors(request):
    """
    Return a dictionary of all available detectors.

    :param request:  HTML Request. (not used for this function)
    :return: A JsonResponse dictionary of detectors. {detector_id: {'id':, 'name': , 'model': }}
    """

    rv = Detector().getall()

    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    rv = {d['detector_id']: d for d in rv.get('detectors').values()}

    return JsonResponse(rv, safe=False)


def get_monitors(request):
    rv = MonitorFactory().getall()

    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    # active_monitors = video_views.get_active_monitors().keys()

    rv = {m['name']: m for m in rv.get('monitors').values()}

    return JsonResponse(rv, safe=False)


def get_monitor(request):
    name = request.GET.get('name')
    if name is None:
        return JsonResponse({'success': False, 'message': "'name' parameter is required.", 'monitor': None})

    obj = MonitorFactory().get(monitor_name=name)
    return JsonResponse(
        {'success': obj.get('success'),
         'monitor': f"{obj.get('monitor')}",
         'message': f"{obj.get('message')}"}, safe=False)


def create_monitor(request):
    """

    :param request: The HTML request that should include values for 'state', 'exclude_counties', 'top_n_counties' and 'data_type'.
    See the parameter descriptions below for constraints and defaults for each parameter.
    :return:
    """
    if request is not None:
        name = request.GET.get('name', None)
        detector_id = request.GET.get('detector_id', None)
        feed_id = request.GET.get('feed_id', None)
        # if name is None or detector_id is None or feed_id is None:
        #     return {'success': False, 'monitor': None, 'message': f"'name', 'detector_id' and 'feed_id' are all required."},

        log_objects = request.GET.get('log_objects', None).split(",")
        notification_objects = request.GET.get('notification_objects', None).split(",")

        obj = MonitorFactory().create(name=name,
                                      detector_id=detector_id,
                                      feed_cam=feed_id,
                                      log_objects=log_objects,
                                      notification_objects=notification_objects)
        return JsonResponse(
            {'success': obj.get('success'), 'monitor': f"{obj.get('monitor')}", 'message': f"{obj.get('message')}"},
            safe=False)


def get_trained_objects(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})
    rv = MonitorFactory().get(monitor_name=monitor_name)
    if not rv['success']:
        return JsonResponse(rv, safe=False)

    return JsonResponse(sorted(list(rv['monitor'].get_trained_objects())), safe=False)


def get_logged_objects(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})
    rv = MonitorFactory().get(monitor_name=monitor_name)
    if not rv['success']:
        return JsonResponse(rv, safe=False)

    return JsonResponse(sorted(list(rv['monitor'].get_logged_objects())), safe=False)


def get_notification_objects(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})
    rv = MonitorFactory().get(monitor_name=monitor_name)
    if not rv['success']:
        return JsonResponse(rv, safe=False)

    return JsonResponse(sorted(list(rv['monitor'].get_notification_objects())), safe=False)


def toggle_logged_object(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})
    rv = MonitorFactory().get(monitor_name=monitor_name)
    if not rv['success']:
        return JsonResponse(rv, safe=False)
    monitor: Monitor = rv['monitor']

    object_name = request.GET.get('object', None)
    if object_name is None:
        return JsonResponse({"success": False, "message": "'object' is a required parameter."}, safe=False)

    rv = monitor.toggle_logged_object(object_name=object_name)

    return JsonResponse(rv, safe=False)


def toggle_notification_object(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})
    rv = MonitorFactory().get(monitor_name=monitor_name)
    if not rv['success']:
        return JsonResponse(rv, safe=False)
    monitor: Monitor = rv['monitor']

    object_name = request.GET.get('object', None)
    if object_name is None:
        return JsonResponse({"success": False, "message": "'object' is a required parameter."}, safe=False)

    rv = monitor.toggle_notification_object(object_name=object_name)

    return JsonResponse(rv, safe=False)


def _set_objects(request, set_type: str):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})
    rv = MonitorFactory().get(monitor_name=monitor_name)
    if not rv['success']:
        return JsonResponse(rv, safe=False)
    monitor: Monitor = rv['monitor']

    objects = [o.strip() for o in request.GET.get('objects', None).split(",")]
    if objects is None:
        return JsonResponse({"success": False, "message": "A comma separated list of 'objects' is required."})

    if set_type == 'log':
        return JsonResponse(monitor.set_log_objects(objects), safe=False)
    elif set_type == 'notify':
        return JsonResponse(monitor.set_notification_objects(objects), safe=False)
    else:
        return JsonResponse({'success': False, 'message': f"Type '{set_type}' not supported."}, safe=False)


def set_log_objects(request):
    return _set_objects(request=request, set_type='log')


def set_notification_objects(request):
    return _set_objects(request=request, set_type='notify')


def start_monitor_service(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})
    rv = MonitorFactory().get(monitor_name=monitor_name)
    if not rv['success']:
        return JsonResponse(rv, safe=False)

    log = bool(request.GET.get('log'))
    notify = bool(request.GET.get('notify'))
    chart = bool(request.GET.get('chart'))

    rv = MonitorFactory().start(monitor_name=monitor_name, log=log, notify=notify, chart=chart)



    return JsonResponse({'success': True, 'monitor_id': ms.monitor.id}, safe=False)


def stop_monitor_service(request, monitor_id: int):
    rv = ActiveMonitorServices().get(monitor_id)
    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    ms = rv.get('monitor_service')
    ms.stop()

    return JsonResponse({'success': True, 'monitor_id': ms.monitor.id}, safe=False)


def get_chart(request, monitor_id: int, interval: int = 0):
    rv = chart_views.get_chart(monitor_id=monitor_id, interval=interval)
    return rv
