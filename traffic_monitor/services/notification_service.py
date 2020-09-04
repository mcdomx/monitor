import logging
import time
from abc import ABC

from traffic_monitor.services.service_abstract import ServiceAbstract

logger = logging.getLogger('notification_service')


class NotificationService(ServiceAbstract, ABC):
    """
    A notification service will perform notification actions based on the existence
    of a condition in a stream of data.
    """

    def __init__(self, monitor_config: dict,
                 output_data_topic: str):
        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.subject_name = f"notificationservice__{self.monitor_name}"
        self.notification_interval = 60
        self.notification_objects = self.monitor_config.get('notification_objects')

    def handle_message(self, msg):
        pass

    def run(self):

        logger.info("Starting notification service .. ")

        while self.running:

            _ = self.poll_kafka()

            # sleep for log interval time
            time.sleep(self.notification_interval)

            try:
                logger.info("Hi! I am notifying. (Please implement me!) -> notification_service.py")
            except Exception as e:
                continue

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped log service.")


