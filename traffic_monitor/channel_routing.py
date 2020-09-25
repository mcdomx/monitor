from django.urls import path

from . import websocket_channels

# The <str> variable is intended to contain the monitor name
websocket_urlpatterns = [
    path('ws/traffic_monitor/log/<str>/', websocket_channels.LogChannel),
    path('ws/traffic_monitor/logdata/<str>/', websocket_channels.LogDataChannel),
    path('ws/traffic_monitor/chart/<str>/', websocket_channels.ChartChannel),
    path('ws/traffic_monitor/config_change/<str>/', websocket_channels.ConfigChange),
    path('ws/traffic_monitor/notification/<str>/', websocket_channels.NotificationChannel),
    path('ws/traffic_monitor/video/<str>/', websocket_channels.VideoChannel),
    path('ws/traffic_monitor/test_video/<cam>/', websocket_channels.TestVideoChannel),
]
