import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from traffic_monitor.views import video_views, chart_views
from traffic_monitor.services.monitor_service_manager import MonitorServiceManager

logger = logging.getLogger('api')


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

    rv = MonitorServiceManager().all_feeds()
    if not rv['success']:
        return JsonResponse(rv, safe=False)

    rv = {s['cam']: s for s in rv.get('feeds').values()}
    return JsonResponse(rv, safe=False)


def get_detectors(request):
    """
    Return a dictionary of all available detector_machines.

    :param request:  HTML Request. (not used for this function)
    :return: A JsonResponse dictionary of detector_machines. {detector_id: {'id':, 'name': , 'model': }}
    """

    rv = MonitorServiceManager().all_detectors()
    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    rv = {d['detector_id']: d for d in rv.get('detector_machines').values()}
    return JsonResponse(rv, safe=False)


def get_monitors(request):
    # rv = MonitorFactory().getall()
    rv = MonitorServiceManager().all_monitors()
    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    # provide a Json serializable response
    rv = {m['name']: m for m in rv.get('monitors').values()}
    return JsonResponse(rv, safe=False)


def get_monitor(request):
    name = request.GET.get('name')
    if name is None:
        return JsonResponse({'success': False, 'message': "'name' parameter is required.", 'monitor': None})

    rv = MonitorServiceManager().get_monitor(monitor_name=name)
    return JsonResponse(
        {'success': rv.get('success'),
         'monitor': f"{rv.get('monitor')}",
         'message': f"{rv.get('message')}"}, safe=False)


def create_monitor(request):
    """

    :param request: The HTML request
    See the parameter descriptions below for constraints and defaults for each parameter.
    :return:
    """
    if request is not None:
        name = request.GET.get('name', None)
        detector_id = request.GET.get('detector_id', None)
        feed_id = request.GET.get('feed_id', None)
        logging_on = bool(request.GET.get('logging_on', True))
        notifications_on = bool(request.GET.get('notifications_on', False))
        charting_on = bool(request.GET.get('charting_on', False))

        log_objects = request.GET.get('log_objects', None).split(",")
        notification_objects = request.GET.get('notification_objects', None).split(",")

        obj = MonitorServiceManager().create_monitor(name=name,
                                                     detector_id=detector_id,
                                                     feed_id=feed_id,
                                                     log_objects=log_objects,
                                                     notification_objects=notification_objects,
                                                     logging_on=logging_on,
                                                     notifications_on=notifications_on,
                                                     charting_on=charting_on)
        return JsonResponse(
            {'success': obj.get('success'), 'monitor': f"{obj.get('monitor')}", 'message': f"{obj.get('message')}"},
            safe=False)


def get_trained_objects(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    rv = MonitorServiceManager().get_trained_objects(monitor_name=monitor_name)
    return JsonResponse(sorted(list(rv)), safe=False)


def get_logged_objects(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    rv = MonitorServiceManager().get_logged_objects(monitor_name)
    return JsonResponse(rv, safe=False)


def get_notification_objects(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    rv = MonitorServiceManager().get_notification_objects(monitor_name)
    return JsonResponse(rv, safe=False)


def toggle_logged_object(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    object_name = request.GET.get('object', None)
    if object_name is None:
        return JsonResponse({"success": False, "message": "'object' is a required parameter."}, safe=False)

    rv = MonitorServiceManager().toggle_logged_object(monitor_name=monitor_name,
                                                      object_name=object_name)

    return JsonResponse(rv, safe=False)


def toggle_notification_object(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    object_name = request.GET.get('object', None)
    if object_name is None:
        return JsonResponse({"success": False, "message": "'object' is a required parameter."}, safe=False)

    rv = MonitorServiceManager().toggle_notification_object(monitor_name=monitor_name,
                                                            object_name=object_name)

    return JsonResponse(rv, safe=False)


def _set_objects(request, set_type: str):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    objects = [o.strip() for o in request.GET.get('objects', None).split(",")]
    if objects is None:
        return JsonResponse({"success": False, "message": "A comma separated list of 'objects' is required."})

    if set_type == 'log':
        return JsonResponse(MonitorServiceManager().set_log_objects(monitor_name=monitor_name, set_objects=objects),
                            safe=False)
    elif set_type == 'notify':
        return JsonResponse(
            MonitorServiceManager().set_notification_objects(monitor_name=monitor_name, set_objects=objects), safe=False)
    else:
        return JsonResponse({'success': False, 'message': f"Type '{set_type}' not supported."}, safe=False)


def set_log_objects(request):
    return _set_objects(request=request, set_type='log')


def set_notification_objects(request):
    return _set_objects(request=request, set_type='notify')


def start_monitor(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    log_interval = request.GET.get('log_interval', 60)
    detection_interval = request.GET.get('detection_interval', 5)

    rv = MonitorServiceManager().start_monitor(monitor_name=monitor_name,
                                               log_interval=log_interval,
                                               detection_interval=detection_interval)

    return JsonResponse(rv, safe=False)


def stop_monitor(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    rv = MonitorServiceManager().stop_monitor(monitor_name)

    return JsonResponse(rv, safe=False)


def get_chart(request, monitor_id: int, interval: int = 0):
    rv = chart_views.get_chart(monitor_id=monitor_id, interval=interval)
    return rv
