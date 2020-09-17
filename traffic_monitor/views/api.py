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

    rv = video_views.toggle_box(action, class_id, monitor_id)

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
        monitors = MonitorServiceManager().all_monitors()
        rv = []
        for m in monitors:
            rv.append(_filter_serializable(m))
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

        mon = MonitorServiceManager().get_monitor_configuration(kwargs.get('name'))

        # only return values that are Json serializable
        rv = _filter_serializable(mon)

        field = kwargs.get('field')
        if field is not None and field in rv.keys():
            rv = rv.get(field)

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


def update_monitor(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'monitor_name')

        mon = MonitorServiceManager().update_monitor(kwargs)

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


def get_all_log_objects(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'monitor_name')
        monitor_name = kwargs.get('monitor_name')

        objects = MonitorServiceManager().get_objects(monitor_name=monitor_name, _type='all_log')
        return JsonResponse(objects, safe=False)
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


def toggle_objects(request, field) -> JsonResponse:
    kwargs = _parse_args(request, 'monitor_name', 'objects')
    kwargs.update({'field': field})
    return JsonResponse(MonitorServiceManager().toggle_objects(**kwargs), safe=False)


def toggle_log_objects(request) -> JsonResponse:
    return toggle_objects(request=request, field='log_objects')


def toggle_notification_objects(request) -> JsonResponse:
    return toggle_objects(request=request, field='notification_objects')


def toggle_chart_objects(request) -> JsonResponse:
    return toggle_objects(request=request, field='charting_objects')


def _set_objects(request, field: str) -> JsonResponse:

    kwargs = _parse_args(request, 'monitor_name', 'objects')
    monitor_name = kwargs.get('monitor_name')
    objects = [o.strip() for o in kwargs.get('objects').split(',')]

    # validate the objects
    valid_objects, invalid_objects = MonitorServiceManager().validate_objects(objects=objects,
                                                                              monitor_name=monitor_name)

    rv = MonitorServiceManager().set_value(monitor_name, field, valid_objects)

    if invalid_objects:
        message = {'message': f"Untrained objects are not considered: {invalid_objects}"}
        rv = {**message, **rv}

    return rv


def set_log_objects(request) -> JsonResponse:
    rv = _set_objects(request, 'log_objects')
    return JsonResponse(rv, safe=False)


def set_log_interval(request) -> JsonResponse:
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'log_interval', int(kwargs.get('value')))
    return JsonResponse(rv, safe=False)


def set_notification_objects(request) -> JsonResponse:
    rv = _set_objects(request=request, field='notification_objects')
    return JsonResponse(rv, safe=False)


def set_chart_objects(request) -> JsonResponse:
    rv = _set_objects(request=request, field='charting_objects')
    return JsonResponse(rv, safe=False)


def set_chart_time_horizon(request) -> JsonResponse:
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'charting_time_horizon', kwargs.get('value'))
    return JsonResponse(rv, safe=False)


def set_chart_time_zone(request) -> JsonResponse:
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'charting_time_zone', kwargs.get('value'))
    return JsonResponse(rv, safe=False)


def detector_sleep_throttle(request) -> JsonResponse:
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'detector_sleep_throttle', int(kwargs.get('value')))
    return JsonResponse(rv, safe=False)


def detector_confidence(request) -> JsonResponse:
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'detector_confidence', float(kwargs.get('value')))
    return JsonResponse(rv, safe=False)


def start_monitor(request):
    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({"success": False, "message": "'monitor_name' of a Monitor is a required parameter."})

    # log_interval = request.GET.get('log_interval', 60)
    # detection_interval = request.GET.get('detection_interval', 5)
    # charting_interval = request.GET.get('charting_interval', 60)
    # notification_interval = request.GET.get('notification_interval', 60)

    rv = MonitorServiceManager().start_monitor(monitor_name=monitor_name)

    return JsonResponse(rv, safe=False)


def stop_monitor(request):
    kwargs = _parse_args(request, 'monitor_name')

    rv = MonitorServiceManager().stop_monitor(**kwargs)

    return JsonResponse(rv, safe=False)


def toggle_service(request):
    kwargs = _parse_args(request, 'monitor_name', 'service')

    rv = MonitorServiceManager().toggle_service(**kwargs)

    return JsonResponse(rv, safe=False)


def get_chart(request):
    kwargs = _parse_args(request, 'monitor_name')
    monitor_config = MonitorServiceManager().get_monitor_configuration(kwargs.get('monitor_name'))
    rv = chart_views.get_chart(monitor_config)

    return JsonResponse(rv, safe=False)


def set_charting_options(request):

    kwargs = _parse_args(request, 'monitor_name') #monitor_name, time_horizon, charted_objects, time_zone

    rv = MonitorServiceManager().set_charting_options(**kwargs)

    return JsonResponse(rv, safe=False)
