import logging
import os
import getpass
import string
import random

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
        """ Create a .env defulat file """
        # Create .env File
        # If there is no .env file, create one with application defaults
        env_file_name = ".env"

        for f in os.listdir():
            if f == env_file_name:
                print(f"I found a {env_file_name} file! No need to create one")
                return

        # If I get here, I didn't find a .env file, let's create one

        # get a password from the user
        print(f"No {env_file_name} file exists.  A default env file will be created.")
        db_name = input("Provide a database name: ")
        db_user = input("Create a database user name: ")

        db_pw1 = getpass.getpass()
        db_pw2 = getpass.getpass("enter again: ")
        while db_pw1 != db_pw2:
            print(">> Passwords do not match.  Try again. <<")
            db_pw1 = getpass.getpass()
            db_pw2 = getpass.getpass("enter again: ")

        f = open(f"{env_file_name}", "w+")
        f.write("export VERBOSITY=INFO\n\n")
        f.write(f"export DB_NAME={db_name}\n")
        f.write(f"export DB_USER={db_user}\n")
        f.write(f"export DB_PASSWORD={db_pw1}\n")
        f.write(f"export DB_HOST=0.0.0.0\n")
        f.write(f"export DB_PORT=5432\n\n")
        letters = string.ascii_letters + string.digits + string.punctuation
        django_secret_key = ''.join(random.choice(letters) for i in range(30))
        django_secret_key = django_secret_key.replace("'", "").replace("\"", "")
        f.write(f"export DJANGO_SECRET_KEY = '{django_secret_key}'\n")

        f.close()





