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


def get_active_monitors(request) -> JsonResponse:
    try:
        active_monitors = MonitorServiceManager().get_active_monitors()

        rv = _filter_serializable(active_monitors)

        # make the response serializable
        return JsonResponse(rv, safe=False)

    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


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
        return JsonResponse({'error': e.args}, safe=False)


def _parse_args(request, *args):
    """
    Helper function that will parse a series of args from a request.
    If an arg is not in the request, an exception is thrown.
    Arguments in the request that are not listed are included in the returned dictionary.
    :param request: The HTTP request that should contain the arguments
    :param args: A series of string values that represent the name of the argument
    :return: A dictionary where keys are the arguments and values the respective values of each argument.
    """

    rv = {}

    for arg_name in args:
        arg_value = request.GET.get(arg_name)
        if not arg_value:
            raise Exception(f"'{arg_name}' parameter is required.")
        rv.update({arg_name: arg_value})

    other_args = set(request.GET.keys()).difference(rv.keys())
    for other_name in other_args:
        rv.update({other_name: request.GET.get(other_name)})

    return rv


def create_stream(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'cam', 'time_zone', 'description')
        rv = MonitorServiceManager().create_stream(**kwargs)
        # only return values that are Json serializable
        rv = _filter_serializable(rv)
        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


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
        return JsonResponse({'error': e.args}, safe=False)


def get_monitors(request) -> JsonResponse:
    try:
        rv = MonitorServiceManager().all_monitors()
        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


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
        except Exception:
            try:
                iter(v)  # test if its iterable
                v = _filter_serializable(v)  # if so, filter it
            except Exception:
                continue

        rv.update({k: v})

    return rv


def get_monitor(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'name')
        # name = request.GET.get('name')
        # if name is None:
        #     raise Exception("'name' parameter is required.")

        mon = MonitorServiceManager().get_monitor(**kwargs)

        # only return values that are Json serializable
        rv = _filter_serializable(mon)

        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def create_monitor(request) -> JsonResponse:
    """

    :param request: The HTML request
    See the parameter descriptions below for constraints and defaults for each parameter.
    :return:
    """
    try:
        kwargs = _parse_args(request, 'name', 'detector_name', 'detector_model', 'feed_id')
        mon = MonitorServiceManager().create_monitor(**kwargs)

        # only return values that are Json serializable
        rv = _filter_serializable(mon)

        return JsonResponse(rv, safe=False)

    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def get_trained_objects(request) -> JsonResponse:
    try:
        monitor_name = request.GET.get('monitor_name', None)
        detector_name = request.GET.get('detector_name', None)
        if monitor_name is None and detector_name is None:
            raise Exception("Either a 'monitor_name' or a 'detector_name' is a required parameter.")

        kwargs = {'monitor_name': monitor_name, 'detector_name': detector_name}

        objects = MonitorServiceManager().get_trained_objects(**kwargs)

        return JsonResponse(sorted(list(objects)), safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def get_log_objects(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'monitor_name')

        objects = MonitorServiceManager().get_objects(**kwargs, _type='log')
        return JsonResponse(sorted(list(objects)), safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def get_notification_objects(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'monitor_name')

        objects = MonitorServiceManager().get_objects(**kwargs, _type='notification')
        return JsonResponse(objects, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def toggle_objects(request, _type: str = None) -> JsonResponse:
    kwargs = _parse_args(request, 'monitor_name', 'objects')

    # the type parameter needs special handling since type is a reserved word
    if 'type' not in kwargs.keys():
        if _type is None:
            return JsonResponse({"success": False, "message": "A 'type' is required. ('log', 'notification')"})
        else:
            kwargs.update({'_type': _type})
    else:
        kwargs.update({'_type': kwargs.get('type')})
        kwargs.pop('type')

    return JsonResponse(MonitorServiceManager().toggle_objects(**kwargs), safe=False)


def toggle_log_objects(request) -> JsonResponse:
    return toggle_objects(request=request, _type='log')


def toggle_notification_objects(request) -> JsonResponse:
    return toggle_objects(request=request, _type='notification')


def _set_objects(request, _type: str) -> JsonResponse:
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    objects = [o.strip() for o in request.GET.get('objects', None).split(",")]
    if objects is None:
        return JsonResponse({"success": False, "message": "A comma separated list of 'objects' is required."})

    return JsonResponse(MonitorServiceManager().set_objects(monitor_name=monitor_name, objects=objects, _type=_type),
                        safe=False)


def set_log_objects(request) -> JsonResponse:
    return _set_objects(request=request, _type='log')


def set_notification_objects(request) -> JsonResponse:
    return _set_objects(request=request, _type='notification')


def start_monitor(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    log_interval = request.GET.get('log_interval', 60)
    detection_interval = request.GET.get('detection_interval', 5)
    charting_interval = request.GET.get('detection_interval', 60)

    rv = MonitorServiceManager().start_monitor(monitor_name=monitor_name,
                                               log_interval=log_interval,
                                               detection_interval=detection_interval,
                                               charting_interval=charting_interval)

    return JsonResponse(rv, safe=False)


def stop_monitor(request):
    kwargs = _parse_args(request, 'monitor_name')

    rv = MonitorServiceManager().stop_monitor(**kwargs)

    return JsonResponse(rv, safe=False)


def get_chart(request, monitor_id: int, interval: int = 0):
    rv = chart_views.get_chart(monitor_id=monitor_id, interval=interval)
    return rv
