import logging

from django.shortcuts import render
from django.http import JsonResponse

from ..models.models import TrafficMonitorFeed
from ..code.forecast import create_forecast


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _parse_args(request, *args):
    """
    Helper function that will parse a series of URL arguments from a request.
    If an argument is not in the request, an exception is thrown.
    Arguments in the request that are not listed are not specified in the args
    argument are included in the returned dictionary even though they were not required.

    Usage:
        kwargs = _parse_args(request, 'required_arg1', 'required_arg2', ..)

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

def get_forecast(request):
    """
    Retrieve a forcast which is structured according to arguments provided:
    'monitor_name': name of monitor to predict
    'interval': default=60. number of minutes in each forecast interval
    'predictor_hours': default=24. number of hours to create predictions for
    'classes_to_predict': defaults to all available if no list of classes is provided.
    'from_date': defaults to first date available.  This is the date where training records are started.
        This option exists in the event that a large dataset is available and not all records are needed
        for training.
    :param request:
    :return:
    """

    try:
        kwargs = _parse_args(request, 'monitor_name')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    if kwargs.get('interval') is None:
        kwargs.update({'interval': 60})
    if kwargs.get('predictor_hours') is None:
        kwargs.update({'predictor_hours': 24})
    if kwargs.get('classes_to_predict') is not None:
        # make the string a list
        c = kwargs.get('classes_to_predict')
        if c == '':
            c = None
        else:
            c = c.split(',')
        kwargs.update({'classes_to_predict': c})

    print(kwargs)

    try:
        fc_data = create_forecast(**kwargs)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    return JsonResponse(fc_data, safe=False)