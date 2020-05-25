from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/traffic_monitor/log/', consumers.LogConsumer),
    path('ws/traffic_monitor/url/', consumers.URLConsumer),
]
