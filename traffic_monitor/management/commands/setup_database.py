import logging

from django.core.management.base import BaseCommand

from django.db import models

from traffic_monitor.models.model_detector import *
from traffic_monitor.models.model_feed import Feed, FeedFactory
from traffic_monitor.services.monitor_service import MonitorService

logger = logging.getLogger('command')


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass
        # parser.add_argument('-mycommand', nargs='?', type=str, default=None)

    def handle(self, *args, **options):
        """ Setup DB with supported Detectors and models"""

        ### DETECTORS
        # erase existing detectors
        dets = Detector.objects.all()
        for d in dets:
            d.delete()

        # Setup this dictionary for each model supported
        detectors = {'cvlib': {'models': ['yolov3-tiny', 'yolov3']}}

        # setup db
        for name, m_dict in detectors.items():
            m_list = m_dict.get('models')
            for m in m_list:
                obj, success = Detector.objects.update_or_create(detector_id=f'{name}__{m}', name=name, model=m)
                obj.save()

        ### FEEDS
        # erase existing feeds
        feeds = Feed.objects.all()
        for f in feeds:
            f.delete()

        feeds = {'JH_MainStreet': {'cam': '1EiC9bvVGnk', 'time_zone': 'US/Mountain'},
                 'JH_Roadhouse': {'cam': '6aJXND_Lfk8', 'time_zone': 'US/Mountain'}}

        for desc, settings in feeds.items():
            rv = FeedFactory().get(cam=settings.get('cam'), time_zone=settings.get('time_zone'))
            if rv.get('success'):
                obj = rv.get('feed')
                obj.description = desc
                obj.save()

        ### MONITOR SERVICES
        # Create default monitor services
        for d in Detector.objects.all().values('detector_id'):
            for f in Feed.objects.all().values('cam'):
                _ = MonitorService(detector_id=d.get('detector_id'), feed_cam=f.get('cam'))
