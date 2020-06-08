"""
This service will push charts to the web page.
"""
import threading
import time
import logging

from traffic_monitor.services.observer import Subject

from traffic_monitor.models.model_logentry import LogEntry

logger = logging.getLogger('log_service')


class ChartService(threading.Thread, Subject):
    """
    This service will read data from the database at a regular interval
    and publish updated chart data based on the results.
    """

    def __init__(self, monitor_id: int, charting_interval: int = 60):
        threading.Thread.__init__(self)
        Subject.__init__(self)
        self.name = "Chart_Service_Thread"
        self.subject_name = f"chartservice__{monitor_id}"
        self.charting_interval = charting_interval
        self.running = False
        self.monitor_id = monitor_id

    def start(self):
        self.running = True
        threading.Thread.start(self)

    def stop(self):
        self.running = False

    def run(self):

        i = 0
        logger.info("Starting chart service ...")
        while self.running:

            time.sleep(self.charting_interval)

            self.publish({'monitor_id': self.monitor_id})

            # logger.info(f"Hi! I'm charting. {i}")

            i += 1
