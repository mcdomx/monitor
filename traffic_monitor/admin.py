from django.contrib import admin

from traffic_monitor.models.models import *


class MonitorAdmin(admin.ModelAdmin):
    list_display = ('name', 'detector', 'feed')
    list_filter = ('detector', 'feed')


admin.site.register(Monitor, MonitorAdmin)


# class ClassAdmin(admin.ModelAdmin):
#     list_display = ('id', 'class_id', 'monitor', 'is_monitoring', 'is_logging')
#     list_filter = ('monitor', 'is_monitoring', 'is_logging')
#
#
# admin.site.register(Class, ClassAdmin)


class FeedAdmin(admin.ModelAdmin):
    list_display = ('cam', 'time_zone', 'description')


admin.site.register(Feed, FeedAdmin)


class DetectorAdmin(admin.ModelAdmin):
    list_display = ('detector_id', 'name', 'model')
    list_filter = ('name', 'model')


admin.site.register(Detector, DetectorAdmin)


class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('time_stamp', 'monitor', 'class_name')
    list_filter = ('monitor', 'time_stamp', 'class_name')


admin.site.register(LogEntry, LogEntryAdmin)


