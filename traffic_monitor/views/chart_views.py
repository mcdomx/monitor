import datetime
import pandas as pd

from traffic_monitor.models.model_logentry import LogEntry

from bokeh.embed import json_item
from bokeh.models import HoverTool, DatetimeTickFormatter
from bokeh.plotting import figure
from bokeh.palettes import brewer
from django.http import JsonResponse
from pygam import LinearGAM, s


def get_chart(monitor_id: int, interval:int):
    tools = [HoverTool(
        tooltips=[
            ("Time", "$x{%m/%d/%y %T}"),
            # https://docs.bokeh.org/en/latest/docs/reference/models/formatters.html#bokeh.models.formatters.DatetimeTickFormatter
            ("Rate", '$y'), ("Object", "@class_id")
        ],
        formatters={'$x': 'datetime'}
        #         , mode='vline'
    )]

    # data
    rs = LogEntry.objects.filter(monitor_id=monitor_id).values('time_stamp', 'class_id', 'count')
    df = pd.DataFrame(rs)
    df.rename(columns={'count': 'counts'}, inplace=True)

    # set timezone
    df = df.set_index('time_stamp').tz_convert('US/Mountain').tz_localize(None)

    # get top 5 items
    top5_classes = df.groupby('class_id').count().sort_values(by='counts', ascending=False).index[0:5].values
    df = df[df['class_id'].isin(top5_classes)]
    df.sort_index(inplace=True)

    # Define the blank canvas of the Bokeh plot that data will be layered on top of
    # Define the blank canvas of the Bokeh plot that data will be layered on top of
    fig = figure(
        sizing_mode="stretch_both",
        tools=tools,
        toolbar_location=None,
        x_axis_type="datetime",
        border_fill_color=None,
        min_border_left=0)

    # Remove classic x and y ticks and chart junk to make things clean
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

    # create plot lines for each class
    u_class_ids = sorted(df.class_id.unique())
    df = df[df.class_id.isin(u_class_ids)]
    colors = brewer['Spectral'][5]
    df['fill_color'] = [colors[u_class_ids.index(c)] for c in df.class_id]

    # Multiple Lines
    for i, class_id in enumerate(top5_classes):
        _df = df[df.class_id == class_id].sort_index()
        _x = (_df.index - _df.index.min()).astype(int)

        _df['smoothed_counts'] = LinearGAM(s(0, lam=1)).fit(_x, _df.counts).predict(_x)

        fig.line(x='time_stamp', y='smoothed_counts', source=_df,
                 legend_label=class_id, color=colors[i], line_width=1.5)
        fig.scatter(x='time_stamp', y='counts', source=_df,
                    color=colors[i], size=2, alpha=.5)

    #     fig.add_layout(legend)
    fig.legend.location = "top_left"
    fig.legend.spacing = 0
    fig.legend.padding = 5

    item = json_item(fig)

    return JsonResponse(item)




