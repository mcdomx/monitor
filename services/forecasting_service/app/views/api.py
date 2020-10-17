from django.shortcuts import render
from django.http import JsonResponse

from ..models.models import TrafficMonitorFeed
from ..code.forecast import create_forecast


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

    kwargs = _parse_args(request, 'monitor_name')

    # feeds = list(TrafficMonitorFeed.objects.all().values())
    fc_data = create_forecast(**kwargs)

    return JsonResponse(fc_data, safe=False)