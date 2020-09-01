"""
This service will push charts to the web page.
"""
# import threading
import time
import logging

# from traffic_monitor.services.observer import Subject
from traffic_monitor.services.service_abstract import ServiceAbstract

logger = logging.getLogger('chart_service')


class ChartService(ServiceAbstract):
    """
    This service will read data from the database at a regular interval
    and publish updated chart data based on the results.
    """

    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str,
                 ):
        ServiceAbstract.__init__(self, monitor_config=monitor_config)
        self.subject_name = f"chartservice__{self.monitor_name}"
        self.charting_interval: int = 60
        self.running = False

    def start(self):
        self.running = True
        ServiceAbstract.start(self)

    def stop(self):
        self.running = False

    def run(self):

        logger.info("Starting chart service ...")
        while self.running:

            time.sleep(self.charting_interval)

            try:
                logger.info("Hi! I am charting. (Please implement me!) -> charting_service.py")
            except Exception as e:
                continue

        logger.info("Stopped chart service.")
