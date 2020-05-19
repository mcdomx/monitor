from django.urls import path

from .views import views

urlpatterns = [
    # Default route
    path("", views.index_view, name="index"),
    path("table.html", views.table_view, name="table"),
    path("profile.html", views.table_view, name="profile"),
    path("video_feed", views.video_feed, name="video_feed"),
]
