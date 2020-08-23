"""
This service will push charts to the web page.
"""
# import threading
import time
import logging

# from traffic_monitor.services.observer import Subject
from traffic_monitor.services.service_abstract import ServiceAbstract

logger = logging.getLogger('log_service')


class ChartService(ServiceAbstract):
    """
    This service will read data from the database at a regular interval
    and publish updated chart data based on the results.
    """

    # def __init__(self, monitor_name: str, charting_interval: int = 60):
    def __init__(self, **kwargs):
        super().__init__()
        # threading.Thread.__init__(self)
        # Subject.__init__(self)
        self.name = "Chart_Service_Thread"
        self.subject_name = f"chartservice__{kwargs.get('monitor_name')}"
        self.charting_interval = kwargs.get('charting_interval')
        self.running = False
        self.monitor_name = kwargs.get('monitor_name')

    def start(self):
        self.running = True
        # threading.Thread.start(self)
        ServiceAbstract.start(self)

    def stop(self):
        self.running = False

    def run(self):

        i = 0
        logger.info("Starting chart service ...")
        while self.running:

            time.sleep(self.charting_interval)

            self.publish({'monitor_name': self.monitor_name})

            # logger.info(f"Hi! I'm charting. {i}")

            i += 1

