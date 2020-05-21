from django.contrib import admin

from traffic_monitor.models.models import *


class ClassAdmin(admin.ModelAdmin):
    list_display = ('key', 'class_id', 'detector', 'monitor', 'log')
    list_filter = ('detector', 'monitor', 'log')


admin.site.register(Class, ClassAdmin)


class ClassFeed(admin.ModelAdmin):
    list_display = ('stream', 'description')


admin.site.register(Feed, ClassFeed)


class DetectorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'model')
    list_filter = ('name', 'model')


admin.site.register(Detector, DetectorAdmin)


class LogAdmin(admin.ModelAdmin):
    list_display = ('key', 'time_stamp', 'detector', 'feed', 'class_id')
    list_filter = ('detector', 'feed', 'time_stamp', 'class_id')


admin.site.register(Log, LogAdmin)


