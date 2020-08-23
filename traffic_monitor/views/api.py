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


def get_streams(request) -> JsonResponse:
    """
    Return a dictionary of all available video streams.

    :param request:  HTML Request. (not used for this function)
    :return: A JsonResponse dictionary of video streams. {stream: {'cam': , 'time_zone': , 'url': ,'description': }}
    """
    try:
        rv = MonitorServiceManager().all_feeds()
        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse([], safe=False)


def get_detectors(request) -> JsonResponse:
    """
    Return a dictionary of all available detector_machines.

    :param request:  HTML Request. (not used for this function)
    :return: A JsonResponse dictionary of detector_machines. {detector_id: {'id':, 'name': , 'model': }}
    """
    try:
        rv = MonitorServiceManager().all_detectors()
        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse([], safe=False)


def get_monitors(request) -> JsonResponse:
    try:
        rv = MonitorServiceManager().all_monitors()
        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse([], safe=False)


def _filter_serializable(filter_me: dict) -> dict:
    """
    Revise a dictionary so only serializable values are included
    :param filter_me:
    :return:
    """
    # only return values that are Json serializable
    rv = {}
    for k, v in filter_me.items():
        try:
            json.dumps(v)
            rv.update({k: v})
        except Exception:
            continue

    return rv


def get_monitor(request) -> JsonResponse:
    try:
        name = request.GET.get('name')
        if name is None:
            raise Exception("'name' parameter is required.")

        mon = MonitorServiceManager().get_monitor(monitor_name=name)

        # only return values that are Json serializable
        rv = _filter_serializable(mon)

        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({}, safe=False)


def create_monitor(request) -> JsonResponse:
    """

    :param request: The HTML request
    See the parameter descriptions below for constraints and defaults for each parameter.
    :return:
    """
    try:
        name = request.GET.get('name', None)
        detector_name = request.GET.get('detector_name', None)
        detector_model = request.GET.get('detector_model', None)
        feed_id = request.GET.get('feed_id', None)
        logging_on = bool(request.GET.get('logging_on', True))
        notifications_on = bool(request.GET.get('notifications_on', False))
        charting_on = bool(request.GET.get('charting_on', False))
        log_objects = [o.strip() for o in request.GET.get('log_objects', None).split(",")]
        notification_objects = [o.strip() for o in request.GET.get('notification_objects', None).split(",")]

        if name is None:
            raise Exception("'name' parameter is required.")
        if detector_name is None:
            raise Exception("'detector_name' parameter is required.")
        if detector_model is None:
            raise Exception("'detector_model' parameter is required.")
        if feed_id is None:
            raise Exception("'feed_id' parameter is required.")

        mon = MonitorServiceManager().create_monitor(name=name,
                                                     detector_name=detector_name,
                                                     detector_model=detector_model,
                                                     feed_id=feed_id,
                                                     log_objects=log_objects,
                                                     notification_objects=notification_objects,
                                                     logging_on=logging_on,
                                                     notifications_on=notifications_on,
                                                     charting_on=charting_on)

        # only return values that are Json serializable
        rv = _filter_serializable(mon)

        return JsonResponse(rv, safe=False)

    except Exception as e:
        logger.error(e)
        return JsonResponse({}, safe=False)


def get_trained_objects(request) -> JsonResponse:
    try:
        monitor_name = request.GET.get('monitor_name', None)
        if monitor_name is None:
            raise Exception("'monitor_name' of a Monitor is a required parameter.")

        objects = MonitorServiceManager().get_trained_objects(monitor_name=monitor_name)
        return JsonResponse(sorted(list(objects)), safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse([], safe=False)


def get_logged_objects(request) -> JsonResponse:
    try:
        monitor_name = request.GET.get('monitor_name', None)
        if monitor_name is None:
            raise Exception("'monitor_name' of a Monitor is a required parameter.")

        objects = MonitorServiceManager().get_logged_objects(monitor_name)
        return JsonResponse(sorted(list(objects)), safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse([], safe=False)


def get_notification_objects(request) -> JsonResponse:
    try:
        monitor_name = request.GET.get('monitor_name', None)
        if monitor_name is None:
            raise Exception("'monitor_name' of a Monitor is a required parameter.")

        objects = MonitorServiceManager().get_notification_objects(monitor_name)
        return JsonResponse(objects, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse([], safe=False)


def toggle_logged_object(request) -> JsonResponse:
    try:
        monitor_name = request.GET.get('monitor_name', None)
        if monitor_name is None:
            raise Exception("'monitor_name' of a Monitor is a required parameter.")

        object_name = request.GET.get('object', None)
        if object_name is None:
            raise Exception("'object' is a required parameter.")

        rv = MonitorServiceManager().toggle_logged_object(monitor_name=monitor_name,
                                                          object_name=object_name)
        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        JsonResponse([], safe=False)


def toggle_notification_object(request) -> JsonResponse:
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    object_name = request.GET.get('object', None)
    if object_name is None:
        return JsonResponse({"success": False, "message": "'object' is a required parameter."}, safe=False)

    rv = MonitorServiceManager().toggle_notification_object(monitor_name=monitor_name,
                                                            object_name=object_name)

    return JsonResponse(rv, safe=False)


def _set_objects(request, set_type: str) -> JsonResponse:
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
        return JsonResponse([], safe=False)


def set_log_objects(request) -> JsonResponse:
    return _set_objects(request=request, set_type='log')


def set_notification_objects(request) -> JsonResponse:
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
