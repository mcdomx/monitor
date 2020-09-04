"""
This service will monitor a queue for entries that should be
logged. The service will summarize entries after a specified
time interval and save the entries to database.
"""

import logging
import json
import datetime
import time

from abc import ABC

from traffic_monitor.models.model_logentry import LogEntry
from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.elapsed_time import ElapsedTime

logger = logging.getLogger('log_service')


class LogService(ServiceAbstract, ABC):
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
        self.log_interval = 60  # freq (in sec) in detections are logged

    def handle_message(self, msg) -> (str, object):
        msg_key = msg.key().decode('utf-8')

        if msg_key == 'detector_detection':
            msg_value = json.JSONDecoder().decode(msg.value().decode('utf-8'))

            return msg_key, msg_value

    def run(self):
        timer = ElapsedTime()
        capture_count = 0
        log_interval_detections = []

        logger.info(f"Starting log service for {self.monitor_name} .. ")
        while self.running:

            msg = self.poll_kafka()
            if msg is None:
                continue

            key_msg = self.handle_message(msg)

            if key_msg is None:
                continue

            msg_key, msg_value = key_msg

            logger.info(f"Logger is handling message for {self.monitor_name}:")
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

            # time.sleep(self.pulse)

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped log service.")
