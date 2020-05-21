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
    context = {'detector_id': 'detector_cvlib__yolov3'}

    return render(request, 'traffic_monitor/index.html', context)


def table_view(request):
    """

    :param request:
    :return:
    """
    return render(request, 'traffic_monitor/table.html')


def profile_view(request):
    """

    :param request:
    :return:
    """
    return render(request, 'traffic_monitor/profile.html')