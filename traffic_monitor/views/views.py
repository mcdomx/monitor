import cv2

from .video_views import *
from traffic_monitor.models.model_class import Class

from django.shortcuts import render


def index_view(request):
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


# def table_view(request):
#     """
#
#     :param request:
#     :return:
#     """
#     return render(request, 'traffic_monitor/table.html')
#
#
# def profile_view(request):
#     """
#
#     :param request:
#     :return:
#     """
#     return render(request, 'traffic_monitor/profile.html')
