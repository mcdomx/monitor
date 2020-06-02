"""
This service will monitor a queue for entries that should be
logged. The service will summarize entries after a specified
time interval and save the entries to database.
"""

import threading
import logging
import queue
import datetime
import pytz
import time

from .elapsed_time import ElapsedTime
from traffic_monitor.models.model_monitor import Monitor
from traffic_monitor.models.model_logentry import LogEntry
from traffic_monitor.consumers import ConsumerFactory
from traffic_monitor.services.observer import Observer, Subject

logger = logging.getLogger('log_service')


class LogService(threading.Thread, Subject):
    def __init__(self, monitor_id: int, queue_dets_log: queue.Queue, log_interval: int):
        threading.Thread.__init__(self)
        Subject.__init__(self)
        self.subject_name = f"logservice__{monitor_id}"
        self.running = False
        self.monitor_id = monitor_id
        self.time_zone = Monitor.get_timezone(monitor_id)
        self.queue_dets_log = queue_dets_log
        self.log_interval = log_interval  # freq (in sec) in detections are logged

    def start(self):
        self.running = True
        threading.Thread.start(self)

    def stop(self):
        self.running = False

    def run(self):
        capture_count = 0
        log_interval_detections = []
        log_interval_timer = ElapsedTime()

        logger.info("Starting log service .. ")
        while self.running:

            try:
                log_interval_detections += self.queue_dets_log.get(block=False)
                capture_count += 1
            except Exception as e:
                continue

            # logger.info(f"picked up detections: {log_interval_detections}")

            # if log interval reached, record average items per minute
            if log_interval_timer.get() >= self.log_interval:

                # Counts the mean observation count at any moment over the log interval period.
                objs_unique = set(log_interval_detections)
                minute_counts_dict = {obj: round(log_interval_detections.count(obj) / capture_count, 3) for obj in
                                      objs_unique}
                timestamp = datetime.datetime.now(tz=pytz.timezone(self.time_zone))

                LogEntry.add(time_stamp=timestamp,
                             monitor_id=self.monitor_id,
                             count_dict=minute_counts_dict)

                logger.info(f"Monitor: {self.monitor_id} Detections: {minute_counts_dict}")

                # update observers
                self.publish({'monitor_id': self.monitor_id, 'timestamp': timestamp, 'counts': minute_counts_dict})

                # publish entry to channel
                # self.log_channel.update({'timestamp': timestamp, 'counts': minute_counts_dict})

                # restart the log interval counter, clear the detections and restart the capture count
                log_interval_timer.reset()
                log_interval_detections.clear()
                capture_count = 0

        logger.info("Stopped log service.")
