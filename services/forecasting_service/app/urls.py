from django.urls import path, re_path

from .views import views

urlpatterns = [
    # External Routes
    path("", views.get_forecast, name="get_forecast"),
]
