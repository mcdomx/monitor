import logging

from django.core.management.base import BaseCommand

from django.db import models

from traffic_monitor.models.model_detector import Detector
from traffic_monitor.models.model_feed import Feed
from traffic_monitor.models.model_monitor import Monitor
from traffic_monitor.services.monitor_service_manager import MonitorServiceManager

logger = logging.getLogger('command')


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass
        # parser.add_argument('-mycommand', nargs='?', type=str, default=None)

    def handle(self, *args, **options):
        """ Setup DB with supported Detectors and models"""

        # DETECTORS
        # first, erase existing detector_machines
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

        # FEEDS
        # first, erase existing feeds
        feeds = Feed.objects.all()
        for f in feeds:
            f.delete()

        feeds = {'JacksonHole_MainStreet': {'cam': '1EiC9bvVGnk', 'time_zone': 'US/Mountain'},
                 'JacksonHole_Roadhouse': {'cam': '6aJXND_Lfk8', 'time_zone': 'US/Mountain'}}

        for desc, settings in feeds.items():
            rv = MonitorServiceManager().create_feed(cam=settings.get('cam'),
                                                     time_zone=settings.get('time_zone'),
                                                     description=desc)
            if rv.get('success'):
                obj = rv.get('feed')
                obj.description = desc
                obj.save()

        # MONITORS
        # Create monitors for all combinations of
        # detector_machines and feeds that are created above.
        # first, erase existing monitors
        monitors = Monitor.objects.all()
        for m in monitors:
            m.delete()

        for d in Detector.objects.all():
            for f in Feed.objects.all():
                _ = MonitorServiceManager().create_monitor(name=f"MON_{f.description}_{d.detector_id}",
                                                           detector_id=d.detector_id,
                                                           feed_id=f.cam,
                                                           log_objects=[],
                                                           notification_objects=[],
                                                           logging_on=True,
                                                           notifications_on=False,
                                                           charting_on=False)
