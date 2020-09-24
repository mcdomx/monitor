from django.urls import path, re_path

from traffic_monitor.views import views
from traffic_monitor.views import video_views
from traffic_monitor.views import api


urlpatterns = [
    # External Routes
    path("", views.index_view, name="index"),
    path("createmonitor", views.create_monitor_view, name="createmonitor"),
    path("createstream", views.create_feed_view, name="createstream"),
    re_path(r"test_video[\/|\?].*", views.test_video, name='test_video'),
    re_path(r"start_test_video_stream[\/|\?].*", views.start_test_video_stream, name='start_test_video_stream'),
    # path("table", views.table_view, name="table"),
    # path("profile", views.profile_view, name="profile"),

    # Internal Routes
    # path("video_feed/<int:monitor_id>", video_views.video_feed, name="video_feed"),

    # API routes
    path("get_timezones", api.get_timezones, name="get_timezones"),
    path("get_streams", api.get_streams, name="get_streams"),
    re_path(r"create_stream[\/|\?].*", api.create_stream, name='create_stream'),
    path("get_detectors", api.get_detectors, name="get_detectors"),

    re_path(r"create_monitor[\/|\?].*", api.create_monitor, name='create_monitor'),
    re_path(r"update_monitor[\/|\?].*", api.update_monitor, name='update_monitor'),
    path("get_monitors", api.get_monitors, name="get_monitors"),
    re_path(r"get_monitor[\/|\?].*", api.get_monitor, name='get_monitor'),

    re_path(r"get_trained_objects[\/|\?].*", api.get_trained_objects, name='get_trained_objects'),
    re_path(r"get_log_objects[\/|\?].*", api.get_log_objects, name='get_log_objects'),
    re_path(r"get_all_log_objects[\/|\?].*", api.get_all_log_objects, name='get_all_log_objects'),
    re_path(r"set_log_interval[\/|\?].*", api.set_log_interval, name='set_log_interval'),
    re_path(r"get_notification_objects[\/|\?].*", api.get_notification_objects, name='get_notified_objects'),

    re_path(r"toggle_log_objects[\/|\?].*", api.toggle_log_objects, name='toggle_log_objects'),
    re_path(r"toggle_notification_objects[\/|\?].*", api.toggle_notification_objects, name='toggle_notification_objects'),
    re_path(r"toggle_chart_objects[\/|\?].*", api.toggle_chart_objects, name='toggle_chart_objects'),

    re_path(r"set_log_objects[\/|\?].*", api.set_log_objects, name='set_log_objects'),
    re_path(r"set_notification_objects[\/|\?].*", api.set_notification_objects, name='set_notification_objects'),
    re_path(r"set_chart_objects[\/|\?].*", api.set_chart_objects, name='set_chart_objects'),
    re_path(r"set_chart_time_horizon[\/|\?].*", api.set_chart_time_horizon, name='set_chart_time_horizon'),
    re_path(r"set_chart_time_zone[\/|\?].*", api.set_chart_time_zone, name='set_chart_time_zone'),
    re_path(r"set_detector_sleep_throttle[\/|\?].*", api.detector_sleep_throttle, name='detector_sleep_throttle'),
    re_path(r"set_detector_confidence[\/|\?].*", api.detector_confidence, name='detector_confidence'),


    re_path(r"start_monitor[\/|\?].*", api.start_monitor, name="start_monitor"),
    re_path(r"stop_monitor[\/|\?].*", api.stop_monitor, name="stop_monitor"),
    path("get_active_monitors", api.get_active_monitors, name="get_active_monitors"),

    re_path(r"toggle_service[\/|\?].*", api.toggle_service, name="toggle_service"),

    re_path(r"get_chart[\/|\?].*", api.get_chart, name="get_chart"),

    re_path(r"get_logged_data[\/|\?].*", api.get_logged_data, name="get_logged_data"),



]
