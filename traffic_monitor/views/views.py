import cv2

from .video_views import *
# from traffic_monitor.models.model_class import Class

from django.shortcuts import render

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


def index_view(request):
    kwargs = _parse_args(request, 'monitor_name')

    return render(request, 'traffic_monitor/base.html', kwargs)


def index_view_old(request):
    """
    Default Index route which shows the initial page
    :param request:
    :return:
    """
    # if not request.user.is_authenticated:
    # create monitor services

    # _ = MonitorService(detector_id='cvlib__yolov3', feed_cam='6aJXND_Lfk8')
    # ms = MonitorService(detector_id='cvlib__yolov3-tiny', feed_cam='1EiC9bvVGnk')
    # ms.start()

    # context = {'monitor_id': ms.monitor.id}
    context = {}

    return render(request, 'traffic_monitor/index.html', context)