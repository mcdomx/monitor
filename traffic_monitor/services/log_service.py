"""
This service will monitor a queue for entries that should be
logged. The service will summarize entries after a specified
time interval and save the entries to database.
"""

# import threading
import logging
import json
import datetime
# import pytz
# import time

# from confluent_kafka import Consumer

from traffic_monitor.models.model_logentry import LogEntry
from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.elapsed_time import ElapsedTime

logger = logging.getLogger('log_service')


class LogService(ServiceAbstract):
    """
    An instance of a log service will create entries into the database on a specified interval.
    The LogService operates as a thread and sleeps until the logging interval is complete.
    Once ready to create the log entry, the LogService will look for detections in a
    referenced queue, clearing the queue and writing the detections from that queue
    into the database.
    """

    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str,
                 ):
        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.subject_name = f"logservice__{monitor_config.get('monitor_name')}"
        self.running = False
        self.log_interval = 60  # freq (in sec) in detections are logged
        # self.log_objects = monitor_config.get('log_objects')
        # self.time_zone = monitor_config.get('time_zone')

    def start(self):
        if self.running:
            return

        self.running = True
        ServiceAbstract.start(self)  # start thread

    def stop(self):
        self.running = False

    def handle_message(self, msg) -> (str, object):
        msg_key = msg.key().decode('utf-8')

        if msg_key == 'detector_detection':
            msg_value = json.JSONDecoder().decode(msg.value().decode('utf-8'))

            return msg_key, msg_value

    def run(self):
        timer = ElapsedTime()
        capture_count = 0
        log_interval_detections = []

        logger.info("Starting log service .. ")
        while self.running:

            msg = self.poll_kafka()
            if msg is None:
                continue

            key_msg = self.handle_message(msg)

            if key_msg is None:
                continue

            msg_key, msg_value = key_msg

            logger.info("Logger is handling message:")
            logger.info(f"\tKEY: {msg_key}")
            logger.info(f"\tMSG: {msg_value}")

            if msg_key != 'detector_detection':
                continue

            time_stamp_type, time_stamp = msg.timestamp()

            capture_count += 1
            log_interval_detections += msg_value

            # if the time reached the the logging interval
            if timer.get() >= self.log_interval:
                # Counts the mean observation count at any moment over the log interval period.
                # Only count items that are on the logged_objects list
                objs_unique = set(log_interval_detections)
                interval_counts_dict = {obj: round(log_interval_detections.count(obj) / capture_count, 3) for obj in
                                        objs_unique if obj in self.monitor_config.get('log_objects')}
                # time is saved in UTC
                timestamp = datetime.datetime.utcfromtimestamp(time_stamp / 1000)

                # add observations to database
                LogEntry.add(time_stamp=timestamp,
                             monitor_name=self.monitor_name,
                             count_dict=interval_counts_dict)
                logger.info(f"Monitor: {self.monitor_name} Logged Detections: {interval_counts_dict}")

                # reset variables for next observation
                log_interval_detections.clear()
                capture_count = 0
                timer.reset()

        self.consumer.close()
        logger.info(f"[{__name__}] Stopped log service.")
