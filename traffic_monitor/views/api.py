import json
import logging
import pytz
from django.http import JsonResponse, HttpResponse

from traffic_monitor.views import chart_views
from traffic_monitor.services.monitor_service_manager import MonitorServiceManager

logger = logging.getLogger('api')


def _parse_args(request, *args):
    """
    Helper function that will parse a series of URL arguments from a request.
    If an argument is not in the request, an exception is thrown.
    Arguments in the request that are not listed are not specified in the args
    argument are included in the returned dictionary even though they were not required.

    :param request: The HTTP request that should contain the arguments
    :param args: A list of string values that represent the names of arguments to parse
    :return: A dictionary where keys are the arguments and values the respective values of each argument in the request.
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


def _filter_serializable(filter_me: dict) -> dict:
    """
    Helper function that will remove elements from a dictionary that are not JSON serializable.

    :param filter_me:  Dictionary that has elements which may be filtered.
    :return:  The original dictionary without elements that are not JSON serializable.
    """
    #  Use recursion to filter nested dictionary elements
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


def get_active_monitors(request) -> JsonResponse:
    """
    Retrieve the currently active monitors hosted by the application.

    API Call:
        /get_active_monitors

    :param request:  HTTP request.
    :return: Dictionary of active monitors where each key is the monitor name and value is a dictionary of k,v pairs of monitor parameters and respective values.
    """
    try:
        active_monitors = MonitorServiceManager().get_active_monitors()

        # make the response serializable
        rv = _filter_serializable(active_monitors)

        return JsonResponse(rv, safe=False)

    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def get_streams(request) -> JsonResponse:
    """
    Return a dictionary of all available video streams configured for the application.

    API Call:
        /get_streams

    :param request:  HTML Request. (not used for this function)
    :return: A JsonResponse dictionary of video streams. {stream: {'cam': , 'time_zone': , 'url': ,'description': }}
    """
    try:
        rv = MonitorServiceManager().all_feeds()
        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def create_stream(request) -> JsonResponse:
    """
    Create a video stream.

    API Call:
        /create_stream?cam=<camera URL>&
        time_zone=<pytz time zone>&
        description=<user defined>

    :param request: HTTP request that requires 'cam', 'time_zone' and 'description' arguments. The 'cam' argument can be any http address to a video stream or a short-hand youtube video hash. The 'time_zone' represents the timezone where the video is sourced from.  A 'description' is a free-form description of the stream.  Stream address and time zones will be validated before being saved. If validation fails, an error will be returned.
    :return: A dictionary of the stream settings that have been set or an error if the stream could not be validated.
    """
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

    API Call:
        /get_detectors

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
    """
    Return a list of all monitors configured in the application.  Each list element is a dictionary representing
    the k,v argument/values for each monitor.

    API Call:
        /get_monitors

    :param request: HTTP request.
    :return: List of dictionaries where each dictionary includes the k,v pairs of the monitor values.
    """
    try:
        monitors = MonitorServiceManager().all_monitors()
        rv = []
        for m in monitors:
            rv.append(_filter_serializable(m))
        return JsonResponse(rv, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def get_monitor(request) -> JsonResponse:
    """
    Return that configuration values of a specified monitor.

    API Call:
        /get_monitor?name=<monitor name>

    :param request: HTTP request that expects a 'monitor_name' argument.
    :return: The full set of configured values for a monitor.
    """
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
    Create a new monitor.

    API Call:
        /create_monitor?
        name=<unique name assigned to monitor>&
        detector_name=<name of detector>&
        detector_model=<existing detector model name>&
        feed_id=<id of existing feed>&
        log_objects=<comma-separated list of objects (optional)>&
        notification_objects=<comma-separated list of objects (optional)>&
        charting_objects=<comma-separated list of objects (optional)>&
        charting_time_zone=<pytz time zone to display chart (optional)>&
        charting_time_horizon=<x-axis time horizon for charting (optional)>


    :param request: The HTML request. See the parameter descriptions below for constraints and defaults for each parameter.
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
    """
    Update parameter values of a monitor.

    API Call:
        /update_monitor?
        detector_name=<name of detector>&
        detector_model=<existing detector model name>&
        feed_id=<id of existing feed>&
        log_objects=<comma-separated list of objects (optional)>&
        notification_objects=<comma-separated list of objects (optional)>&
        charting_objects=<comma-separated list of objects (optional)>&
        charting_time_zone=<pytz time zone to display chart (optional)>&
        charting_time_horizon=<x-axis time horizon for charting (optional)>

    :param request: HTTP request that expects a 'monitor_name' and argument=value parameter settings for each parameter to set.
    :return: The full list of parameters for the monitor after settings have been applied.
    """
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
    """
    Return a list of objects trained by a detector.  The detector can be determined by a 'monitor_name'
    or 'detector_name'.

    API Call:
        /get_trained_objects?
        monitor_name=<monitor name>&
        detector_name=<detector name>

    :param request: HTTP request the expects either a 'detector_name' or 'monitor_name' argument.
    :return:
    """
    try:
        monitor_name = request.GET.get('monitor_name', None)
        detector_name = request.GET.get('detector_name', None)
        if monitor_name is None and detector_name is None:
            raise Exception("Either a 'monitor_name' or a 'detector_name' is a required parameter.")

        kwargs = {'monitor_name': monitor_name, 'detector_name': detector_name}

        objects = MonitorServiceManager().get_trained_objects(**kwargs)

        return JsonResponse(sorted(list(objects)), safe=False)
    except Exception as e:
        logger.error({'error': e.args})
        return JsonResponse({'error': e.args}, safe=False)


def get_log_objects(request) -> JsonResponse:
    """
    Retrieve a list of the objects that a monitor will save to the log.

    API Call:
        /get_log_objects?
        monitor_name=<monitor name>

    :param request: HTTP request that includes a 'monitor_name' argument.
    :return: A list of objects that a named monitor will log.
    """
    try:
        kwargs = _parse_args(request, 'monitor_name')

        objects = MonitorServiceManager().get_objects(**kwargs, _type='log')
        return JsonResponse(sorted(list(objects)), safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def get_all_log_objects(request) -> JsonResponse:
    """
    Get a distinct list of all objects that have been logged by a monitor.

    API Call:
        /get_all_log_objects?
        monitor_name=<monitor name>

    :param request: HTTP request with a monitor_name argument.
    :return: A list of distinct objects that have been logged by a monitor.
    """
    try:
        kwargs = _parse_args(request, 'monitor_name')
        monitor_name = kwargs.get('monitor_name')

        objects = MonitorServiceManager().get_objects(monitor_name=monitor_name, _type='all_log')
        return JsonResponse(objects, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def get_notification_objects(request) -> JsonResponse:
    """
    Get a distinct list of all objects that will trigger notifications for a monitor.

    API Call:
        /get_notification_objects?
        monitor_name=<monitor name>

    :param request: HTTP request with a 'monitor_name' argument.
    :return: A list of distinct objects that will trigger a notification.
    """
    try:
        kwargs = _parse_args(request, 'monitor_name')

        objects = MonitorServiceManager().get_objects(**kwargs, _type='notification')
        return JsonResponse(objects, safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)


def _toggle_objects(request, field) -> JsonResponse:
    """
    Add or remove items from a set.  'log_objects' and 'notification_objects' fields are supported.
    Objects are validated before being added to a list.

    :param request: HTTP request that includes a 'monitor_name' and 'objects' argument.
    :param field: The monitor field name that includes items that should be toggled. (log_objects or notification_objects).
    :return: The new list of objects after being toggled.
    """
    kwargs = _parse_args(request, 'monitor_name', 'objects')
    kwargs.update({'field': field})
    return JsonResponse(MonitorServiceManager().toggle_objects(**kwargs), safe=False)


def toggle_log_objects(request) -> JsonResponse:
    """
    Add or remove objects from the 'log_objects' list in a monitor.

    API Call:
        /toggle_log_objects?
        monitor_name=<monitor name>&
        objects=<comma-separated list of objects to toggle>

    :param request: HTTP request that expects a 'monitor_name' and 'objects' arguments.
    :return: The new list of objects after being toggled.
    """
    return _toggle_objects(request=request, field='log_objects')


def toggle_notification_objects(request) -> JsonResponse:
    """
    Add or remove objects from the 'notification_objects' list in a monitor.

    API Call:
        /toggle_notification_objects?
        monitor_name=<monitor name>&
        objects=<comma-separated list of objects to toggle>

    :param request: HTTP request that expects a 'monitor_name' and 'objects' arguments.
    :return: The new list of objects after being toggled.
    """
    return _toggle_objects(request=request, field='notification_objects')


def toggle_chart_objects(request) -> JsonResponse:
    """
    Add or remove objects from the 'charting_objects' list in a monitor.

    API Call:
        /toggle_chart_objects?
        monitor_name=<monitor name>&
        objects=<comma-separated list of objects to toggle>

    :param request: HTTP request that expects a 'monitor_name' and 'objects' arguments.
    :return: The new list of objects after being toggled.
    """
    return _toggle_objects(request=request, field='charting_objects')


def _set_objects(request, field: str) -> JsonResponse:
    """
    Helper function for setting a list of values.

    :param request: HTTP request that expects a 'monitor_name' and 'objects' arguments.
    :param field: The monitor field name that will be set.
    :return: The new list of items after being set.
    """

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
    """
    Set the 'log_objects' of a monitor.

    API Call:
        /set_log_objects?
        monitor_name=<monitor name>&
        objects=<comma-separated list of objects to toggle>

    :param request: HTTP request that expects a 'monitor_name' and 'objects' arguments.
    :return: The new list of items after being set.
    """
    rv = _set_objects(request, 'log_objects')
    return JsonResponse(rv, safe=False)


def set_notification_objects(request) -> JsonResponse:
    """
    Set the 'notification_objects' of a monitor.

    API Call:
        /set_notification_objects?
        monitor_name=<monitor name>&
        objects=<comma-separated list of objects to toggle>

    :param request: HTTP request that expects a 'monitor_name' and 'objects' arguments.
    :return: The new list of items after being set.
    """
    rv = _set_objects(request=request, field='notification_objects')
    return JsonResponse(rv, safe=False)


def set_chart_objects(request) -> JsonResponse:
    """
    Set the 'charting_objects' of a monitor.

    API Call:
        /set_chart_objects?
        monitor_name=<monitor name>&
        objects=<comma-separated list of objects to toggle>

    :param request: HTTP request that expects a 'monitor_name' and 'objects' arguments.
    :return: The new list of items after being set.
    """
    rv = _set_objects(request=request, field='charting_objects')
    return JsonResponse(rv, safe=False)


def set_log_interval(request) -> JsonResponse:
    """
    Set the logging interval of a monitor.

    API Call:
        /set_log_interval?
        monitor_name=<monitor name>&
        value=<log interval value to set>

    :param request: HTTP request that expects a 'monitor_name' and 'value' argument. 'value' represents the new log interval to be set.
    :return:  The new value after being set or the old value if it was not set.
    """
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'log_interval', kwargs.get('value'))
    return JsonResponse(rv, safe=False)


def set_chart_time_horizon(request) -> JsonResponse:
    """
    Set the x-axis (time horizon) of a chart.

    API Call:
        /set_chart_time_horizon?
        monitor_name=<monitor name>&
        value=<time horizon to set>

    :param request: HTTP request that expects a 'monitor_name' and 'value' argument. 'value' represents the new time horizon to be set. Valid time horizons are: 'day', 'week', 'month', 'year', or an integer representing a number of most recent hours to display.
    :return:  The new value after being set or the old value if it was not set.
    """
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'charting_time_horizon', kwargs.get('value'))
    return JsonResponse(rv, safe=False)


def set_chart_time_zone(request) -> JsonResponse:
    """
    Set the time zone of a chart.

    API Call:
        /set_chart_time_zone?
        monitor_name=<monitor name>&
        value=<time zone to set>

    :param request: HTTP request that expects a 'monitor_name' and 'value' argument. 'value' represents the new time zone to be used. Time zones must adhere to the list of valid time zones supported by the pytz module.
    :return:  The new value after being set or the old value if it was not set.
    """
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'charting_time_zone', kwargs.get('value'))
    return JsonResponse(rv, safe=False)


def detector_sleep_throttle(request) -> JsonResponse:
    """
    Set the number of seconds that a detector should sleep after performing a detection.  Increasing this value will
    lower the number of detections performed per minute and lower the CPU burden.

    API Call:
        /detector_sleep_throttle?
        monitor_name=<monitor name>&
        value=<throttle value in seconds to set>

    :param request: HTTP request that expects a 'monitor_name' and 'value' argument. 'value' represents the new sleep time to be set.
    :return:  The new value after being set or the old value if it was not set.
    """
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'detector_sleep_throttle', int(kwargs.get('value')))
    return JsonResponse(rv, safe=False)


def detector_confidence(request) -> JsonResponse:
    """
    Set the confidence that a detector should use when recognizing an object.

    API Call:
        /detector_confidence?
        monitor_name=<monitor name>&
        value=<confidence value from 0 to 1 to set>

    :param request: HTTP request that expects a 'monitor_name' and 'value' argument. 'value' represents the new confidence. The 'value' is expected to be a float value between 0 and 1 (inclusive).
    :return:  The new value after being set or the old value if it was not set.
    """
    kwargs = _parse_args(request, 'monitor_name', 'value')
    rv = MonitorServiceManager().set_value(kwargs.get('monitor_name'), 'detector_confidence', float(kwargs.get('value')))
    return JsonResponse(rv, safe=False)


def start_monitor(request):
    """
    Start a monitor.  Once started, the monitor will begin performing that actions of each enabled service in a
    loop that can be stopped with stop_monitor().

    API Call:
        /start_monitor?
        monitor_name=<monitor name>

    :param request: HTTP request that expects a monitor_name argument.
    :return: A message indicating the status of the monitor.
    """
    kwargs = _parse_args(request, 'monitor_name')
    monitor_name = kwargs.get('monitor_name')
    rv = MonitorServiceManager().start_monitor(monitor_name=monitor_name)

    return JsonResponse(rv, safe=False)


def stop_monitor(request):
    """
    Stops an active monitor.

    API Call:
        /stop_monitor?
        monitor_name=<monitor name>

    :param request: HTTP request that expects a monitor_name argument.
    :return: A message indicating the status of the monitor.
    """
    kwargs = _parse_args(request, 'monitor_name')
    monitor_name = kwargs.get('monitor_name')
    rv = MonitorServiceManager().stop_monitor(monitor_name=monitor_name)

    return JsonResponse(rv, safe=False)


def toggle_service(request):
    """
    Toggle a service on or off depending on its current status.

    API Call:
        /toggle_service?
        monitor_name=<monitor name>&
        service=<name of service to toggle on or off 'log'|'notification'|'chart'>

    :param request: HTTP request that expects a 'monitor_name' and 'service' argument. Supported services are 'log', 'notification' and 'chart'.
    :return: The status of the service after toggle is complete.
    """
    kwargs = _parse_args(request, 'monitor_name', 'service')
    rv = MonitorServiceManager().toggle_service(**kwargs)
    return JsonResponse(rv, safe=False)


def get_chart(request):
    """
    Return a JSON serialized Bokeh chart.

    API Call:
        /get_chart?
        monitor_name=<monitor name>

    :param request: HTTP request that expects a monitor_name argument.
    :return: A JSON serialized Bokeh chart.
    """
    kwargs = _parse_args(request, 'monitor_name')
    monitor_config = MonitorServiceManager().get_monitor_configuration(kwargs.get('monitor_name'))
    rv = chart_views.get_chart(monitor_config)

    return JsonResponse(rv, safe=False)


def get_timezones(request):
    """
    Return a list of all the supported timezone values.
    :return: List of support timezone values
    """
    tzlist = pytz.all_timezones

    rv = {}
    for tz in tzlist:
        split = tz.split('/')
        c = '/'.join(split[:-1])
        if c is '':
            c = "Other"
        z = split[-1]
        if c in rv.keys():
            rv.get(c).append(z)
        else:
            rv.update({c: [z]})

    return JsonResponse(rv, safe=False)
