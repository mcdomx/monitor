"""
This service will push charts to the web page.
"""
# import threading
import time
import logging

# from traffic_monitor.services.observer import Subject
from abc import ABC

from traffic_monitor.services.service_abstract import ServiceAbstract

logger = logging.getLogger('chart_service')


class ChartService(ServiceAbstract, ABC):
    """
    This service will read data from the database at a regular interval
    and publish updated chart data based on the results.
    """

    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str,
                 ):
        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.subject_name = f"chartservice__{self.monitor_name}"
        self.charting_interval: int = 60

    def handle_message(self, msg):
        return None

    def run(self):

        logger.info("Starting chart service ...")
        while self.running:

            _ = self.poll_kafka()

            time.sleep(self.charting_interval)

            try:
                logger.info("Hi! I am charting. (Please implement me!) -> charting_service.py")
            except Exception:
                continue

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped log service.")
