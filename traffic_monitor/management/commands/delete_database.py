import logging

from django.core.management.base import BaseCommand

from traffic_monitor.models.models import *


logger = logging.getLogger('command')


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass
        # parser.add_argument('-mycommand', nargs='?', type=str, default=None)

    def handle(self, *args, **options):
        rs = Class.objects.all()
        i = 0
        for r in rs:
            r.delete()
            i += 1

        if i:
            logger.info(f"Deleted Entries in Table 'Class'. All {i} entries deleted.")
        else:
            logger.info(f"No entries in table 'Class'. No entries deleted.")

        rs = Detector.objects.all()
        i = 0
        for r in rs:
            r.delete()
            i += 1

        if i:
            logger.info(f"Deleted Entries in Table 'Detector'. All {i} entries deleted.")
        else:
            logger.info(f"No entries in table 'Detector'. No entries deleted.")
