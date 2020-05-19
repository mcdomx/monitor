import cv2

from .video_views import *

from django.shortcuts import render


def index_view(request):
    """
    Default Index route which shows the initial page
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return render(request, 'monitor/index.html')


def table_view(request):
    """

    :param request:
    :return:
    """
    return render(request, 'monitor/table.html')


def profile_view(request):
    """

    :param request:
    :return:
    """
    return render(request, 'monitor/profile.html')