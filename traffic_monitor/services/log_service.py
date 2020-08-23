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
from traffic_monitor.services.observer import Subject
from traffic_monitor.services.service_abstract import ServiceAbstract

logger = logging.getLogger('log_service')


class LogService(ServiceAbstract):

    # def __init__(self, monitor_name: str, queue_dets_log: queue.Queue, log_interval: int, time_zone: str):
    def __init__(self, **kwargs):
        super().__init__()
        # threading.Thread.__init__(self)
        # Subject.__init__(self)
        self.subject_name = f"logservice__{kwargs.get('monitor_name')}"
        self.running = False
        self.monitor_name = kwargs.get('monitor_name')
        self.time_zone = kwargs.get('time_zone')
        self.queue_dets_log = kwargs.get('queue_dets_log')
        self.log_interval = kwargs.get('log_interval')  # freq (in sec) in detections are logged

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

            # collect the detections from the queue
            try:
                while True:
                    log_interval_detections += self.queue_dets_log.get(block=False)
                    capture_count += 1

            # once all the queued items are collected, summarize and record them
            except queue.Empty:
                # Counts the mean observation count at any moment over the log interval period.
                objs_unique = set(log_interval_detections)
                minute_counts_dict = {obj: round(log_interval_detections.count(obj) / capture_count, 3) for obj in
                                      objs_unique}
                timestamp = datetime.datetime.now(tz=pytz.timezone(self.time_zone))

                # add observations to database
                LogEntry.add(time_stamp=timestamp,
                             monitor_name=self.monitor_name,
                             count_dict=minute_counts_dict)
                logger.info(f"Monitor: {self.monitor_name} Detections: {minute_counts_dict}")

                # update observers
                self.publish({'monitor_id': self.monitor_name, 'timestamp': timestamp, 'counts': minute_counts_dict})

                # reset variables for next observation
                log_interval_detections.clear()
                capture_count = 0

        logger.info("Stopped log service.")
