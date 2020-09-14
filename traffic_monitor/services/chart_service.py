"""
This service will push charts to the web page.
"""
from datetime import datetime, timezone, timedelta
import logging
from abc import ABC

# import numpy as np
import pandas as pd
from bokeh.embed import json_item
from bokeh.models import HoverTool, DatetimeTickFormatter
from bokeh.plotting import figure
from bokeh.colors import RGB
from pygam import LinearGAM, s
from django.core.serializers.json import DjangoJSONEncoder

from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.websocket_channels import ChartChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory
from traffic_monitor.models.model_logentry import LogEntry
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
        If the configuration changes, we should redraw the chart by sending
        a message through the ChartChannel.
        :param msg:
        :return:
        """
        pass
        # msg_key = msg.key().decode('utf-8')
        # if msg_key == 'config_change':
        #     channel: ChartChannel = ChannelFactory().get(self.channel_url)
        #     if channel:
        #         msg = self.get_chart(monitor_name=self.monitor_name)
        #         channel.send(text_data=DjangoJSONEncoder().encode(msg))
        #
        #         return msg_key, msg

    # def _get_timedelta(self) -> (timedelta, str):
    #     """
    #     Helper function that converts the monitor_config time horizon into a timedelta object.
    #     :return:
    #     """
    #     time_horizon = self.monitor_config.get('charting_time_horizon').lower()
    #     try:
    #         return datetime.now(tz=timezone.utc)-timedelta(hours=int(time_horizon)), f"Last {time_horizon} Hours"
    #     except ValueError:
    #         if time_horizon == 'year':
    #             return datetime.now(tz=timezone.utc)-timedelta(days=365), f"Last {time_horizon.capitalize()}"
    #         if time_horizon == 'month':
    #             return datetime.now(tz=timezone.utc)-timedelta(days=31), f"Last {time_horizon.capitalize()}"
    #         if time_horizon == 'week':
    #             return datetime.now(tz=timezone.utc)-timedelta(days=7), f"Last {time_horizon.capitalize()}"
    #         if time_horizon == 'day':
    #             return datetime.now(tz=timezone.utc)-timedelta(hours=24), f"Last {time_horizon.capitalize()}"
    #
    # def get_chart(self, monitor_name: str):
    #     """
    #     Get a Bokeh chart that shows the trend of detected items recorded in the Log database.
    #     :param monitor_name: Name of monitor to chart
    #     :return:
    #     """
    #     tools = [HoverTool(
    #         tooltips=[
    #             ("Time", "$x{%m/%d/%y %T}"),
    #             # https://docs.bokeh.org/en/latest/docs/reference/models/formatters.html#bokeh.models.formatters.DatetimeTickFormatter
    #             ("Rate", '$y'), ("Object", "@class_name")
    #         ],
    #         formatters={'$x': 'datetime'}
    #         #         , mode='vline'
    #     )]
    #
    #     # get logentries according to the time horizon and charted_objects
    #     time_ago, time_delta_description = self._get_timedelta()
    #     rs = LogEntry.objects.filter(monitor__name=monitor_name,
    #                                  time_stamp__gt=time_ago,
    #                                  class_name__in=self.monitor_config.get('charting_objects')).values('time_stamp', 'class_name', 'count')
    #     if len(rs) == 0:
    #         return None
    #
    #     df = pd.DataFrame(rs)
    #     df.rename(columns={'count': 'counts'}, inplace=True)
    #
    #     # set timezone
    #     df = df.set_index('time_stamp').tz_convert(self.monitor_config.get('charting_time_zone')).tz_localize(None)
    #
    #     # get items in the charted_objects list
    #     # c_obj_len = min(len(self.monitor_config.get('charting_objects')), 11)
    #
    #     if len(df) == 0:
    #         return 'No data for time period.  Wait for detections ... '
    #
    #     # Define the blank canvas of the Bokeh plot that data will be layered on top of
    #     fig = figure(
    #         title=f"{self.monitor_name} - {time_delta_description}",
    #         sizing_mode="stretch_both",
    #         tools=tools,
    #         toolbar_location=None,
    #         x_axis_type="datetime",
    #         border_fill_color=None,
    #         min_border_left=0,
    #         background_fill_color='lightslategrey',
    #         background_fill_alpha=.5)
    #
    #     # Remove default x and y tick marks make chart look clean
    #     fig.xgrid.grid_line_color = None
    #     fig.xaxis.axis_line_color = None
    #     fig.yaxis.axis_line_color = None
    #     fig.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
    #     fig.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
    #     fig.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
    #     fig.yaxis.minor_tick_line_color = None  # turn off y-axis minor ticks
    #
    #     # Hide hours and minutes in the x-axis
    #     fig.xaxis.formatter = DatetimeTickFormatter(
    #         days="%m/%d/%Y",
    #         months="%m/%Y",
    #         hours="%H:%M",
    #         minutes="",
    #         seconds="%m/%d/%Y %H:%M:%S")
    #
    #     fig.xaxis.axis_label = self.monitor_config.get('charting_time_zone')
    #
    #     # create plot lines for each class
    #     u_class_names = sorted(df.class_name.unique())
    #     df = df[df.class_name.isin(u_class_names)]
    #     # colors = brewer['Spectral'][c_obj_len]
    #     # df['fill_color'] = [colors[u_class_names.index(c)] for c in df.class_name]
    #
    #     # Multiple Lines
    #     for i, class_name in enumerate(u_class_names):
    #         _df = df[df.class_name == class_name].sort_index()
    #         _x = (_df.index - _df.index.min()).astype(int)
    #
    #         # smooth trend line using LinearGAM
    #         _df['smoothed_counts'] = LinearGAM(s(0, lam=1)).fit(_x, _df.counts).predict(_x)
    #
    #         # fig.line(x='time_stamp', y='smoothed_counts', source=_df,
    #         #          legend_label=class_name, color=RGB(*self.class_colors.get(class_name)), line_width=3)
    #         # fig.scatter(x='time_stamp', y='counts', source=_df,
    #         #             fill_color=RGB(*self.class_colors.get(class_name)), size=3, alpha=.5, line_color='black', line_width=.3)
    #         fig.line(x='time_stamp', y='smoothed_counts', source=_df,
    #                  legend_label=class_name, color=RGB(*self.monitor_config.get('class_colors').get(class_name)), line_width=3)
    #         fig.scatter(x='time_stamp', y='counts', source=_df,
    #                     fill_color=RGB(*self.monitor_config.get('class_colors').get(class_name)), size=3, alpha=.5, line_color='black',
    #                     line_width=.3)
    #
    #
    #     fig.legend.location = "top_left"
    #     fig.legend.spacing = 0
    #     fig.legend.padding = 5
    #
    #     item = json_item(fig)
    #
    #     return item

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

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped charting service.")
