import datetime
from django.db import models
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.model_feed import Feed


class Log(models.Model):
    key = models.CharField(max_length=128, primary_key=True)
    time_stamp = models.DateTimeField()
    detector = models.ForeignKey(Detector, on_delete=models.SET_NULL, related_name='detector_log', null=True)
    feed = models.ForeignKey(Feed, on_delete=models.SET_NULL, related_name='feed_log', null=True)
    class_id = models.CharField(max_length=32)
    count = models.IntegerField(default=0)

    @staticmethod
    def add(time_stamp: datetime, detector_name: str, count_dict: dict):
        t = f"{time_stamp.year}_{time_stamp.month}_{time_stamp.day}_{time_stamp.hour}_{time_stamp.minute}_{time_stamp.second}"
        add_list = []
        for class_id, count in count_dict.items():
            add_list.append(Log.objects.create(key=f"{t}_{detector_name}",
                                               time_stamp=t,
                                               detector_name=detector_name,
                                               class_id=class_id,
                                               count=count))
        Log.objects.bulk_create(add_list)
