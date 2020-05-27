from django.contrib import admin

from traffic_monitor.models.models import *


class ClassAdmin(admin.ModelAdmin):
    list_display = ('key', 'class_id', 'detector_id', 'monitor', 'log')
    list_filter = ('detector_id', 'monitor', 'log')


admin.site.register(Class, ClassAdmin)


class FeedAdmin(admin.ModelAdmin):
    list_display = ('cam', 'time_zone', 'description')


admin.site.register(Feed, FeedAdmin)


class DetectorAdmin(admin.ModelAdmin):
    list_display = ('detector_id', 'name', 'model')
    list_filter = ('name', 'model')


admin.site.register(Detector, DetectorAdmin)


class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('time_stamp', 'monitor', 'class_id')
    list_filter = ('monitor', 'time_stamp', 'class_id')


admin.site.register(LogEntry, LogEntryAdmin)


