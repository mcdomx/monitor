from django.db import models
from traffic_monitor.models.model_detector import Detector


class Feed(models.Model):
    stream = models.CharField(max_length=256, primary_key=True)
    description = models.CharField(max_length=64)

