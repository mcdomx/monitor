import logging

from django.core.management.base import BaseCommand

from django.db import models

from traffic_monitor.models.models import *


logger = logging.getLogger('command')


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass
        # parser.add_argument('-mycommand', nargs='?', type=str, default=None)

    def handle(self, *args, **options):

        def del_table(table: models.Model, name: str):

            rs = table.objects.all()

            i = 0
            for r in rs:
                r.delete()
                i += 1

            if i:
                logger.info(f"Deleted Entries in Table '{name}'. All {i} entries deleted.")
            else:
                logger.info(f"No entries in table '{name}'. No entries deleted.")

        del_table(Class, "Class")
        del_table(Feed, "Feed")
        del_table(LogEntry, "Feed")
        del_table(Detector, "Detector")
        del_table(Monitor, "Monitor")

