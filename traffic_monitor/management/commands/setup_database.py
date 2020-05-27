import logging

from django.core.management.base import BaseCommand

from django.db import models

from traffic_monitor.models.model_detector import *


logger = logging.getLogger('command')


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass
        # parser.add_argument('-mycommand', nargs='?', type=str, default=None)

    def handle(self, *args, **options):
        """ Setup DB with supported Detectors and models"""

        # Setup this dictionary for each model supported
        detectors = {'cvlib': {'models': ['yolov3-tiny', 'yolov3']}}

        # setup db
        for name, m_dict in detectors.items():
            m_list = m_dict.values()
            for m in m_list:
                obj, success = Detector.objects.update_or_create(detector_id=f'{name}__{m}', name=name, model=m)
                obj.save()
