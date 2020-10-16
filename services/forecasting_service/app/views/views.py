from django.shortcuts import render
from django.http import JsonResponse

from ..models.models import TrafficMonitorFeed


def get_forecast(request):

    feeds = list(TrafficMonitorFeed.objects.all().values())

    return JsonResponse(feeds, safe=False)

