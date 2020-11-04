from django.urls import path, re_path

from .views import api

urlpatterns = [
    # External Routes
    # re_path(r"get_forecast[\/|\?].*", api.get_forecast, name="get_forecast"),
    re_path(r"train[\/|\?].*", api.train, name="train"),
    re_path(r"predict[\/|\?].*", api.predict, name="predict"),
    re_path(r"get_available_models[\/|\?].*", api.get_available_models, name="get_available_models"),
    re_path(r"get_model[\/|\?].*", api.get_model_by_filename, name="get_model_by_filename"),
    re_path(r"update[\/|\?].*", api.retrain, name="update"),
    re_path(r"update_all[\/|\?].*", api.update_all, name="update_all"),
    re_path(r"delete[\/|\?].*", api.delete, name="delete"),
]
