
from django.db import models


class Detector(models.Model):
    detector_id = models.CharField(max_length=128, primary_key=True)
    name = models.CharField(max_length=64)
    model = models.CharField(max_length=64)
