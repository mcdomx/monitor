from django.urls import path

from traffic_monitor.views import views
from traffic_monitor.views import video_views
from traffic_monitor.views import api


urlpatterns = [
    # External Routes
    path("", views.index_view, name="index"),
    path("table", views.table_view, name="table"),
    path("profile", views.profile_view, name="profile"),

    # Internal Routes
    path("video_feed/<int:monitor_id>", video_views.video_feed, name="video_feed"),

    # API routes
    path("get_class_data/<int:monitor_id>", api.get_class_data, name="get_class_data"),
    path("toggle_box", api.toggle_box, name="toggle_box"),
    path("toggle_all/<int:monitor_id>/<action>", api.toggle_all, name="toggle_all"),
    path("get_active_monitors", api.get_active_monitors, name="get_active_monitors"),
    path("get_all_monitors", api.get_all_monitors, name="get_all_monitors"),
    path("monitor/start/<int:monitor_id>", api.start_monitor, name="start_monitor"),
    path("monitor/stop/<int:monitor_id>", api.stop_monitor, name="stop_monitor"),


]
