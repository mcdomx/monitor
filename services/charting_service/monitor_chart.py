# Based on bokeh example
# https://github.com/bokeh/bokeh/blob/branch-2.3/examples/app/sliders.py

import logging
from datetime import datetime, timezone, timedelta
import requests
import json
import pytz
import os
import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.models import HoverTool, DatetimeTickFormatter
from bokeh.plotting import figure
from pygam import LinearGAM, s
from bokeh.colors import RGB
from bokeh.models import ColumnDataSource, CustomJS, DatePicker, DateRangeSlider
from bokeh.driving import count
from bokeh.layouts import column, row

logging.basicConfig(level=logging.INFO)

BOKEH_URL = os.getenv('BOKEH_URL', '127.0.0.1')
BOKEH_PORT = os.getenv('PORT', '8100')
DATA_URL = os.getenv('DATA_URL', '127.0.0.1')
DATA_PORT = os.getenv('DATA_PORT', '8000')


def _get_timedelta(monitor_config) -> (timedelta, str):
    """
    Helper function that converts the monitor_config time horizon into a timedelta object.
    :return:
    """
    time_horizon = monitor_config.get('charting_time_horizon', 'day').lower()
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


def _get_logdata(monitor_name):
    response = requests.get(f'http://{DATA_URL}:{DATA_PORT}/get_logdata?monitor_name={monitor_name}')
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return []


def _get_logdata_bokeh(monitor_name, start_date='1970-01-01T00:00:00.000000', start_date_gt=None):
    start_field = 'start_date'
    if start_date_gt:
        start_field = 'start_date_gt'
        start_date = start_date_gt
    if start_date is None:
        start_date = '1970-01-01T00:00:00.000000'
    response = requests.get(
        f'http://{DATA_URL}:{DATA_PORT}/get_logdata_bokeh?monitor_name={monitor_name}&{start_field}={start_date}')
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return {}


def _get_monitorconfig(monitor_name):
    response = requests.get(f'http://{DATA_URL}:{DATA_PORT}/get_monitor?monitor_name={monitor_name}')
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return None


def change_date(attr, old, new):
    # Incoming new value is a tuple of epoch formatted date
    # attr = 'value'
    new_start_date = datetime.fromtimestamp(new[0] / 1000)
    new_end_date = datetime.fromtimestamp(new[1] / 1000)
    _filter_sources(new_start_date, new_end_date, None)


def _filter_sources(start_date, end_date, objects):
    # change SOURCE_SCATTER so it spans start_date to end_date and include objects
    # dates in datetime format
    global DATA, SOURCE_SCATTER
    data_df = pd.DataFrame(DATA)
    data_df = data_df[(data_df.time_stamp >= start_date) & (data_df.time_stamp <= end_date)]
    SOURCE_SCATTER.data = data_df.to_dict()

    _df = SOURCE_SCATTER.to_df().pivot_table(index='time_stamp', columns='class_name').fillna(0)
    _xs = (_df.index - _df.index.min()).total_seconds().astype(int)
    c_names = list(_df[('count',)].columns)

    # create a column with the LineaGam values
    for c in c_names:
        _df[('line', c)] = np.clip(
            LinearGAM(s(0, n_splines=60, lam=1)).fit(_xs, _df[('count', c)]).predict(_xs), a_min=0,
            a_max=None)

    SOURCE_LINE.data = {'xs': [sorted(set(SOURCE_SCATTER.data['time_stamp'])) for _ in c_names],
                        'ys': [_df[('line', c)].values for c in c_names],
                        'line_color': [COLORS.get(c) for c in c_names],
                        'class_names': c_names}


args = curdoc().session_context.request.arguments
MONITOR_NAME = args.get('monitor_name')[0].decode()
try:
    START_DATE = args.get('start_date')[0].decode()
except:
    START_DATE = None

MONITOR_CONFIG = _get_monitorconfig(MONITOR_NAME)
TIME_ZONE = pytz.timezone(MONITOR_CONFIG.get('time_zone'))
print(f"MONITOR NAME: {MONITOR_CONFIG.get('monitor_name')}")
print(f"TIME_ZONE: {MONITOR_CONFIG.get('time_zone')}")

# SETUP DATA - DATA has all available data for the monitor
DATA = _get_logdata_bokeh(MONITOR_NAME)
LAST_POSTED_TIME = DATA['time_stamp'][-1]
DATA['time_stamp'] = [datetime.strptime(t[:25], "%Y-%m-%dT%H:%M:%S.%f").astimezone(TIME_ZONE) for t in
                      DATA['time_stamp']]
COLORS = json.loads(requests.get(
    f'http://{DATA_URL}:{DATA_PORT}/get_monitor?monitor_name={MONITOR_NAME}&field=class_colors').text)[
    'class_colors']
COLORS = {k: RGB(*c) for k, c in COLORS.items()}
DATA['color'] = [COLORS.get(class_name) for class_name in DATA['class_name']]

SOURCE_SCATTER = ColumnDataSource(data=DATA)

# create df with time_stamp as index and class_name's as columns. NaN's are 0.
DATA_DF = SOURCE_SCATTER.to_df().pivot_table(index='time_stamp', columns='class_name').fillna(0)
_line_xs = (DATA_DF.index - DATA_DF.index.min()).total_seconds().astype(int)
CLASS_NAMES = list(DATA_DF[('count',)].columns)

# create a column with the LineaGam values
for c in CLASS_NAMES:
    DATA_DF[('line', c)] = np.clip(
        LinearGAM(s(0, n_splines=60, lam=1)).fit(_line_xs, DATA_DF[('count', c)]).predict(_line_xs), a_min=0,
        a_max=None)

SOURCE_LINE = ColumnDataSource(data={'xs': [sorted(set(SOURCE_SCATTER.data['time_stamp'])) for _ in CLASS_NAMES],
                                     'ys': [DATA_DF[('line', c)].values for c in CLASS_NAMES],
                                     'line_color': [COLORS.get(c) for c in CLASS_NAMES],
                                     'class_names': CLASS_NAMES})

# setup widgets
DATE_RANGE_SLIDER = DateRangeSlider(value=(min(DATA['time_stamp']), max(DATA['time_stamp'])),
                                    start=min(DATA['time_stamp']),
                                    end=max(DATA['time_stamp']))
DATE_RANGE_SLIDER.on_change("value", change_date)


def get_chart():
    """
    Get a Bokeh chart that shows the trend of detected items recorded in the Log database.
    :param monitor_config:
    :return:
    """
    hover_tool = HoverTool(
        tooltips=[
            ("Time", "$x{%m/%d/%y %T}"),
            # https://docs.bokeh.org/en/latest/docs/reference/models/formatters.html#bokeh.models.formatters.DatetimeTickFormatter
            ("Rate", '$y'), ("Object", "@class_name")
        ],
        formatters={'$x': 'datetime'}
        #         , mode='vline'
    )

    tools = [hover_tool, "pan", "wheel_zoom", "zoom_in", "zoom_out", "reset", "tap", "lasso_select", "box_select"]

    # Define the blank canvas of the Bokeh plot that data will be layered on top of
    fig = figure(
        title=f"{MONITOR_NAME}",
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
    fig.xaxis.axis_label = TIME_ZONE.zone

    # CREATE SCATTER PLOTS
    fig.scatter(x='time_stamp', y='count',
                fill_color='color', legend_field='class_name', line_color='black',
                size=3, alpha=.5, line_width=.3,
                source=SOURCE_SCATTER)

    # CREATE LINE PLOTS
    fig.multi_line(xs='xs', ys='ys',
                   line_color='line_color',
                   line_width=3,
                   source=SOURCE_LINE)

    fig.legend.location = "top_left"
    fig.legend.spacing = 0
    fig.legend.padding = 5

    return fig


@count()
def update(i):
    # i = int representing the number of times this function has been called
    global LAST_POSTED_TIME
    new_data = _get_logdata_bokeh(MONITOR_NAME, start_date_gt=LAST_POSTED_TIME)
    # print(f"GET LEN: {len(data)} T: {t} LAST_POSTED: {last_posted_time}")
    if len(new_data) < 1:
        return
    # print("PROCESSING:")
    print(new_data)
    last_posted_time = new_data['time_stamp'][-1]
    # print(f"SET NEW LAST_POSTED TIME: f{last_posted_time}")
    new_data['time_stamp'] = [datetime.strptime(t[:25], "%Y-%m-%dT%H:%M:%S.%f").astimezone(TIME_ZONE) for t in
                              new_data['time_stamp']]

    colors = json.loads(
        requests.get(f'http://{DATA_URL}:{DATA_PORT}/get_monitor?monitor_name={MONITOR_NAME}&field=class_colors').text)[
        'class_colors']
    colors = {k: RGB(*c) for k, c in colors.items()}
    new_data['color'] = [colors.get(class_name) for class_name in new_data['class_name']]

    SOURCE_SCATTER.stream(new_data, rollover=None)

    _df = SOURCE_SCATTER.to_df().pivot(index='time_stamp', columns='class_name').fillna(0)
    _line_xs = (_df.index - _df.index.min()).total_seconds().astype(int)

    # create a column with the LineaGam values
    class_names = list(_df[('count',)].columns)
    for c in class_names:
        _df[('line', c)] = np.clip(
            LinearGAM(s(0, n_splines=60, lam=1)).fit(_line_xs, _df[('count', c)]).predict(_line_xs), a_min=0,
            a_max=None)

    global SOURCE_LINE
    SOURCE_LINE.data = {'xs': [sorted(set(SOURCE_SCATTER.data['time_stamp'])) for _ in class_names],
                        'ys': [_df[('line', c)].values for c in class_names],
                        'line_color': [colors.get(c) for c in class_names],
                        'class_names': list(class_names)}


if MONITOR_NAME:
    plot = get_chart()

    curdoc().add_root(column(DATE_RANGE_SLIDER, plot))
    curdoc().add_periodic_callback(update, 30000)  # 30000 = 30seconds
    curdoc().title = f"{MONITOR_NAME}"
