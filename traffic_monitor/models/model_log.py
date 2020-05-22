import datetime
from django.db import models
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.model_feed import Feed


class Log(models.Model):
    key = models.BigAutoField(primary_key=True)
    time_stamp = models.DateTimeField()
    detector = models.ForeignKey(Detector, on_delete=models.CASCADE, related_name='detector_log', null=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='feed_log', null=True)
    class_id = models.CharField(max_length=32)
    count = models.IntegerField(default=0)

    @staticmethod
    def add(time_stamp: datetime, detector_id: str, feed_id: str, count_dict: dict):
        for class_id, count in count_dict.items():
            obj = Log.objects.create(time_stamp=time_stamp,
                               detector=Detector.objects.get(pk=detector_id),
                               feed=Feed.objects.get(id=feed_id),
                               class_id=class_id,
                               count=count)
            obj.save()
