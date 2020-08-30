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

    def __init__(self, **kwargs):
        super().__init__()
        self.subject_name = f"logservice__{kwargs.get('monitor_name')}"
        self.running = False
        self.monitor_name = kwargs.get('monitor_name')
        self.time_zone = kwargs.get('time_zone')
        self.log_objects = kwargs.get('log_objects')
        self.queue_dets_log = kwargs.get('queue_dets_log')  # ref to queue in Monitor where detections are stored for logging
        self.log_interval = kwargs.get('log_interval')  # freq (in sec) in detections are logged

    def update(self, subject_info: tuple):
        """
        Calling update() with a subject_info tuple, will send the tuple of data to
        any observers that are registered with the Monitor.

        :param subject_info:
        :return: None
        """
        logger.info(f"{[{__name__}]} :UPDATED WITH: {subject_info}")
        self._handle_update('Monitor', subject_info)

    def start(self):
        self.running = True
        # threading.Thread.start(self)
        ServiceAbstract.start(self)

    def stop(self):
        self.running = False

    def run(self):
        capture_count = 0
        log_interval_detections = []

        logger.info("Starting log service .. ")
        while self.running:

            # sleep for log interval time
            time.sleep(self.log_interval)

            try:
                # collect the detections from the queue - fails when empty
                log_interval_detections += self.queue_dets_log.get(block=False)
                capture_count += 1

            # once all the queued items are collected, summarize and record them
            except queue.Empty:
                # Counts the mean observation count at any moment over the log interval period.
                # Only count items that are on the logged_objects list
                objs_unique = set(log_interval_detections)
                minute_counts_dict = {obj: round(log_interval_detections.count(obj) / capture_count, 3) for obj in
                                      objs_unique if obj in self.log_objects}
                timestamp = datetime.datetime.now(tz=pytz.timezone(self.time_zone))

                # add observations to database
                LogEntry.add(time_stamp=timestamp,
                             monitor_name=self.monitor_name,
                             count_dict=minute_counts_dict)
                logger.info(f"Monitor: {self.monitor_name} Logged Detections: {minute_counts_dict}")

                # update observers
                self.publish({'monitor_id': self.monitor_name, 'timestamp': timestamp, 'counts': minute_counts_dict})

                # reset variables for next observation
                log_interval_detections.clear()
                capture_count = 0

        logger.info("Stopped log service.")
