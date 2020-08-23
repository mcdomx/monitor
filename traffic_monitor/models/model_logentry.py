import datetime
from django.db import models
from traffic_monitor.models.model_monitor import Monitor


class LogEntry(models.Model):
    key = models.BigAutoField(primary_key=True)
    time_stamp = models.DateTimeField()
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, related_name='monitor_log', null=True)
    class_name = models.CharField(max_length=32)
    count = models.FloatField(default=0)

    @staticmethod
    def add(time_stamp: datetime, monitor_name: str, count_dict: dict):
        for class_name, count in count_dict.items():
            obj = LogEntry.objects.create(time_stamp=time_stamp,
                                          monitor=Monitor.objects.get(pk=monitor_name),
                                          class_name=class_name,
                                          count=count)
            obj.save()
