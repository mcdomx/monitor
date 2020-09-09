"""
This service will push charts to the web page.
"""
# import threading
import time
import logging
import json
from abc import ABC

from django.core.serializers.json import DjangoJSONEncoder

from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.websocket_channels import ChartChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory

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
        self.channel_url = f"/ws/traffic_monitor/chart/{monitor_config.get('monitor_name')}/"  # websocket channel address

    def handle_message(self, msg):
        msg_key = msg.key().decode('utf-8')

        if msg_key == 'chart_data':
            msg_value = json.JSONDecoder().decode(msg.value().decode('utf-8'))

            return msg_key, msg_value

    def run(self):

        logger.info("Starting chart service ...")
        while self.running:

            msg = self.poll_kafka(0)
            if msg is None:
                continue

            key_msg = self.handle_message(msg)
            if key_msg is None:
                continue

            try:
                # send web-client updates using the Channels-Redis websocket
                channel: ChartChannel = ChannelFactory().get(self.channel_url)
                # only use the channel if a channel has been created
                if channel:
                    # this sends message to ay front end that has created a WebSocket
                    # with the respective channel_url address
                    time_stamp_type, time_stamp = msg.timestamp()
                    msg_key, msg_value = key_msg
                    msg = {'time_stamp': time_stamp,
                           'monitor_name': self.monitor_name,
                           'key': msg_key,
                           'chart_data': msg_value}
                    channel.send(text_data=DjangoJSONEncoder().encode(msg))
            except Exception as e:
                logger.info(e)
                continue

            time.sleep(self.charting_interval)

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped charting service.")
