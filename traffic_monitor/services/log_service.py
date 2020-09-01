"""
This service will monitor a queue for entries that should be
logged. The service will summarize entries after a specified
time interval and save the entries to database.
"""

# import threading
import logging
import queue
import datetime
import pytz
import time

from confluent_kafka import Consumer

from traffic_monitor.models.model_logentry import LogEntry
from traffic_monitor.services.service_abstract import ServiceAbstract

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
        ServiceAbstract.__init__(self, monitor_config=monitor_config)
        self.subject_name = f"logservice__{monitor_config.get('monitor_name')}"
        self.running = False
        self.output_data_topic = output_data_topic
        self.log_interval = 60  # freq (in sec) in detections are logged

    def start(self):
        self.running = True
        ServiceAbstract.start(self)  # start thread

    def stop(self):
        self.running = False

    def run(self):
        capture_count = 0
        log_interval_detections = []

        consumer = Consumer({
            'bootstrap.servers': '127.0.0.1',
            'group.id': 'monitorgroup',
            'auto.offset.reset': 'earliest'
        })

        consumer.subscribe([self.monitor_config.get('monitor_name')])

        logger.info("Starting log service .. ")
        while self.running:

            msg = consumer.poll(1.0)

            if msg is None:
                continue
            if msg.error():
                logger.info(f"[{__name__}] Consumer error: {msg.error()}")
                continue

            # decode message and reformat undersrocres
            msg = msg.value().decode('utf-8').split(' ')
            msg = [d.replace('_', ' ') for d in msg]

            logger.info(f"[{__name__}] Received message: {msg}")

            # sleep for log interval time
            # time.sleep(self.log_interval)

            # try:
            #     # collect the detections from the queue - fails when empty
            #     log_interval_detections += self.queue_dets_log.get(block=False)
            #     capture_count += 1
            #
            # # once all the queued items are collected, summarize and record them
            # except queue.Empty:
            #     # Counts the mean observation count at any moment over the log interval period.
            #     # Only count items that are on the logged_objects list
            #     objs_unique = set(log_interval_detections)
            #     minute_counts_dict = {obj: round(log_interval_detections.count(obj) / capture_count, 3) for obj in
            #                           objs_unique if obj in self.log_objects}
            #     timestamp = datetime.datetime.now(tz=pytz.timezone(self.time_zone))
            #
            #     # add observations to database
            #     LogEntry.add(time_stamp=timestamp,
            #                  monitor_name=self.monitor_name,
            #                  count_dict=minute_counts_dict)
            #     logger.info(f"Monitor: {self.monitor_name} Logged Detections: {minute_counts_dict}")
            #
            #     # update observers
            #     self.publish({'monitor_id': self.monitor_name, 'timestamp': timestamp, 'counts': minute_counts_dict})
            #
            #     # reset variables for next observation
            #     log_interval_detections.clear()
            #     capture_count = 0

        consumer.close()
        logger.info(f"[{__name__}] Stopped log service.")
