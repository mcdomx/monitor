import logging
import time
from abc import ABC
import json

from django.core.serializers.json import DjangoJSONEncoder

from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.websocket_channels import NotificationChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory

logger = logging.getLogger('notification_service')


class NotificationService(ServiceAbstract, ABC):
    """
    A notification service will perform notification actions based on the existence
    of a condition in a stream of data.
    """

    def __init__(self, monitor_config: dict, output_data_topic: str):
        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.subject_name = f"notificationservice__{self.monitor_name}"
        self.notification_interval = 60
        self.notification_objects = self.monitor_config.get('notification_objects')
        self.channel_url = f"/ws/traffic_monitor/notification/{monitor_config.get('monitor_name')}/"  # websocket channel address

    def handle_message(self, msg):
        msg_key = msg.key().decode('utf-8')

        if msg_key == 'notification':
            msg_value = json.JSONDecoder().decode(msg.value().decode('utf-8'))

            return msg_key, msg_value

    def run(self):

        logger.info("Starting notification service ...")
        while self.running:

            msg = self.poll_kafka(0)
            if msg is None:
                continue

            key_msg = self.handle_message(msg)
            if key_msg is None:
                continue

            try:
                # send web-client updates using the Channels-Redis websocket
                channel: NotificationChannel = ChannelFactory().get(self.channel_url)
                # only use the channel if a channel has been created
                if channel:
                    # this sends message to ay front end that has created a WebSocket
                    # with the respective channel_url address
                    time_stamp_type, time_stamp = msg.timestamp()
                    msg_key, msg_value = key_msg
                    msg = {'time_stamp': time_stamp,
                           'monitor_name': self.monitor_name,
                           'key': msg_key,
                           'notification_data': msg_value}
                    channel.send(text_data=DjangoJSONEncoder().encode(msg))
            except Exception as e:
                logger.info(e)
                continue

            self.condition.acquire()
            self.condition.wait(self.notification_interval)
            self.condition.release()
            # time.sleep(self.notification_interval)

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped notification service.")
