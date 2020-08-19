from django.urls import path, re_path

from traffic_monitor.views import views
from traffic_monitor.views import video_views
from traffic_monitor.views import api


urlpatterns = [
    # External Routes
    path("", views.index_view, name="index"),
    # path("table", views.table_view, name="table"),
    # path("profile", views.profile_view, name="profile"),

    # Internal Routes
    path("video_feed/<int:monitor_id>", video_views.video_feed, name="video_feed"),

    # API routes
    path("get_streams", api.get_streams, name="get_streams"),
    path("get_detectors", api.get_detectors, name="get_detectors"),

    re_path(r"create_monitor[\/|\?].*", api.create_monitor, name='create_monitor'),
    path("get_monitors", api.get_monitors, name="get_monitors"),
    re_path(r"get_monitor[\/|\?].*", api.get_monitor, name='get_monitor'),

    re_path(r"create_monitor_service[\/|\?].*", api.create_monitor_service, name='create_monitor_service'),
    path("get_monitor_services", api.get_monitor_services, name="get_monitor_services"),
    re_path(r"get_monitor_service[\/|\?].*", api.get_monitor_service, name='get_monitor_service'),

    re_path(r"get_trained_objects[\/|\?].*", api.get_trained_objects, name='get_trained_objects'),
    re_path(r"toggle_log_object[\/|\?].*", api.toggle_log_object, name='toggle_log_object'),
    re_path(r"get_logged_objects[\/|\?].*", api.get_logged_objects, name='get_logged_objects'),

    re_path(r"toggle_notified_object[\/|\?].*", api.toggle_notified_object, name='toggle_notified_object'),
    re_path(r"get_notified_objects[\/|\?].*", api.get_notified_objects, name='get_notified_objects'),


    # path("get_class_data/<int:monitor_id>", api.get_class_data, name="get_class_data"),
    path("toggle_box", api.toggle_box, name="toggle_box"),
    path("toggle_all/<int:monitor_id>/<action>", api.toggle_all, name="toggle_all"),
    path("get_active_monitors", api.get_active_monitors, name="get_active_monitors"),



    path("monitor/start/<int:monitor_id>", api.start_monitor, name="start_monitor"),
    path("monitor/stop/<int:monitor_id>", api.stop_monitor, name="stop_monitor"),
    path("get_chart/<int:monitor_id>", api.get_chart, name="get_chart"),


]
