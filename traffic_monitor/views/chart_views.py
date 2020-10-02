import logging
from datetime import datetime, timezone, timedelta
import pandas as pd

from bokeh.embed import json_item
from bokeh.models import HoverTool, DatetimeTickFormatter
from bokeh.plotting import figure
from pygam import LinearGAM, s
from bokeh.colors import RGB

from traffic_monitor.models.model_logentry import LogEntry

logger = logging.getLogger('view')


def _get_timedelta(monitor_config) -> (timedelta, str):
    """
    Helper function that converts the monitor_config time horizon into a timedelta object.
    :return:
    """
    time_horizon = monitor_config.get('charting_time_horizon').lower()
    try:
        return datetime.now(tz=timezone.utc) - timedelta(hours=int(time_horizon)), f"Last {time_horizon} Hours"
    except ValueError:
        if time_horizon == 'year':
            return datetime.now(tz=timezone.utc) - timedelta(days=365), f"Last {time_horizon.capitalize()}"
        if time_horizon == 'month':
            return datetime.now(tz=timezone.utc) - timedelta(days=31), f"Last {time_horizon.capitalize()}"
        if time_horizon == 'week':
            return datetime.now(tz=timezone.utc) - timedelta(days=7), f"Last {time_horizon.capitalize()}"
        if time_horizon == 'day':
            return datetime.now(tz=timezone.utc) - timedelta(hours=24), f"Last {time_horizon.capitalize()}"


def get_chart(monitor_config: dict):
    """
    Get a Bokeh chart that shows the trend of detected items recorded in the Log database.
    :param monitor_config:
    :return:
    """

    tools = [HoverTool(
        tooltips=[
            ("Time", "$x{%m/%d/%y %T}"),
            # https://docs.bokeh.org/en/latest/docs/reference/models/formatters.html#bokeh.models.formatters.DatetimeTickFormatter
            ("Rate", '$y'), ("Object", "@class_name")
        ],
        formatters={'$x': 'datetime'}
        #         , mode='vline'
    )]

    # get logentries according to the time horizon and charted_objects
    time_ago, time_delta_description = _get_timedelta(monitor_config)
    rs = LogEntry.objects.filter(monitor__name=monitor_config.get('monitor_name'),
                                 time_stamp__gt=time_ago,
                                 class_name__in=monitor_config.get('charting_objects')).values('time_stamp',
                                                                                               'class_name',
                                                                                               'count')
    if len(rs) == 0:
        return {'success': False, 'message': "No data available for parameters selected. Wait for detections or change parameters."}

    df = pd.DataFrame(rs)
    df.rename(columns={'count': 'counts'}, inplace=True)

    # set timezone
    try:
        df = df.set_index('time_stamp').tz_convert(monitor_config.get('charting_time_zone')).tz_localize(None)
    except Exception:
        df = df.set_index('time_stamp').tz_convert(monitor_config.get('time_zone')).tz_localize(None)

    if len(df) == 0:
        return {'success': False, 'message': "No data available for parameters selected. Wait for detections or change parameters."}

    # Define the blank canvas of the Bokeh plot that data will be layered on top of
    fig = figure(
        title=f"{monitor_config.get('monitor_name')} - {time_delta_description}",
        sizing_mode="stretch_both",
        tools=tools,
        toolbar_location=None,
        x_axis_type="datetime",
        border_fill_color=None,
        min_border_left=0,
        background_fill_color='lightslategrey',
        background_fill_alpha=.5)

    # Remove default x and y tick marks make chart look clean
    fig.xgrid.grid_line_color = None
    fig.xaxis.axis_line_color = None
    fig.yaxis.axis_line_color = None
    fig.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
    fig.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
    fig.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
    fig.yaxis.minor_tick_line_color = None  # turn off y-axis minor ticks

    # Hide hours and minutes in the x-axis
    fig.xaxis.formatter = DatetimeTickFormatter(
        days="%m/%d/%Y",
        months="%m/%Y",
        hours="%H:%M",
        minutes="",
        seconds="%m/%d/%Y %H:%M:%S")

    fig.xaxis.axis_label = monitor_config.get('charting_time_zone')

    # create plot lines for each class
    u_class_names = sorted(df.class_name.unique())
    df = df[df.class_name.isin(u_class_names)]

    # Multiple Lines
    for i, class_name in enumerate(u_class_names):
        _df = df[df.class_name == class_name].sort_index()
        _x = (_df.index - _df.index.min()).astype(int)

        # smooth trend line using LinearGAM
        # _df['smoothed_counts'] = LinearGAM(s(0, lam=1)).fit(_x, _df.counts).predict(_x)
        _df['smoothed_counts'] = LinearGAM(s(0, n_splines=60, lam=1)).fit(_x, _df.counts).predict(_x)

        fig.line(x='time_stamp', y='smoothed_counts', source=_df,
                 legend_label=class_name, color=RGB(*monitor_config.get('class_colors').get(class_name)),
                 line_width=3)
        fig.scatter(x='time_stamp', y='counts', source=_df,
                    fill_color=RGB(*monitor_config.get('class_colors').get(class_name)), size=3, alpha=.5,
                    line_color='black',
                    line_width=.3)

    fig.legend.location = "top_left"
    fig.legend.spacing = 0
    fig.legend.padding = 5

    item = json_item(fig)

    return item
