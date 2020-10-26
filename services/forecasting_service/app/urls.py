from django.urls import path, re_path

from .views import api

urlpatterns = [
    # External Routes
    # re_path(r"get_forecast[\/|\?].*", api.get_forecast, name="get_forecast"),
    re_path(r"train[\/|\?].*", api.train, name="train"),
    re_path(r"predict[\/|\?].*", api.predict, name="train"),
]
