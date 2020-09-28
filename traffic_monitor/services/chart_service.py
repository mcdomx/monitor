"""
This service will push charts to the web page.
"""
from datetime import datetime, timezone, timedelta
import logging
from abc import ABC

from django.core.serializers.json import DjangoJSONEncoder

from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.websocket_channels import ChartChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory
from traffic_monitor.views import chart_views

logger = logging.getLogger('chart_service')


class ChartService(ServiceAbstract, ABC):
    """
    This service will read data from the database at a regular interval
    and publish updated chart data based on the results.
    """

    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str
                 ):
        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.subject_name = f"chartservice__{self.monitor_name}"
        self.charting_interval: int = 60
        self.channel_url = f"/ws/traffic_monitor/chart/{monitor_config.get('monitor_name')}/"  # websocket channel address

        # class colors must be integer RGB values for bokeh charting
        # self.class_colors = {cls: np.uint8(color) for cls, color in self.class_colors.items()}

    def handle_message(self, msg):
        """
        :param msg:
        :return:
        """
        pass

    def run(self):

        logger.info("Starting chart service ...")
        while self.running:
            try:
                # let config changes be handled by abstract class
                # no need to locally handle message
                _ = self.poll_kafka(0)

                # send web-client updates using the Channels-Redis websocket
                channel: ChartChannel = ChannelFactory().get(self.channel_url)

                # only use the channel if a channel has been created
                if channel:
                    # this sends message to ay front end that has created a WebSocket
                    # The message is the bokeh chart object in json format
                    json_chart = chart_views.get_chart(monitor_config=self.monitor_config)
                    # Only send out a message if there are records to plot
                    if json_chart:
                        channel.send(text_data=DjangoJSONEncoder().encode(json_chart))

            except Exception as e:
                logger.error("Unknown exception triggered in chart_service.py run() loop.")
                logger.error(e)
                continue

            # enter a disruptable sleep
            self.condition.acquire()
            self.condition.wait(self.charting_interval)
            self.condition.release()

        # make sure that running is false in case something else stopped this loop
        self.running = False

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped charting service.")
