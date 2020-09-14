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

        # MONITORS
        # For all monitors that do not have class colors assigned, create a class color assignment
        monitors = Monitor.objects.all()
        for m in monitors:
            if len(m.class_colors) == 0:
                m.class_colors = MonitorServiceManager().make_class_colors(m.detector.name)
                m.save()
                logger.info(f"Created {len(m.class_colors)} class colors for {m.name}")
