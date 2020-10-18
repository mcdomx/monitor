"""
This module will create a Bokeh chart in an HTML page which can be embedded in another page.
All available data is first downloaded into a DATA_DF dataframe.  New updates of data are
added to DATA_DF and added to the embedded chart.  When the user changes the range of the chart,
the DATA_DF dataframe is used to build new data sources for the chart.  The chart includes
a scatter plot and a line plot that shows the scatter trend.  When updated, the trend line
is calculated with data before and after the presented scatter plot so trend lines flow on the ends.
"""

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
from time import sleep

from bokeh.io import curdoc
from bokeh.models import HoverTool, DatetimeTickFormatter
from bokeh.plotting import figure
from pygam import LinearGAM, s
from bokeh.colors import RGB
from bokeh.models import ColumnDataSource, DateRangeSlider, Select, CustomJS, Spacer
from bokeh.driving import count
from bokeh.layouts import column, row

logging.basicConfig(level=logging.INFO)


DATA_URL = os.getenv('DATA_URL', '127.0.0.1')
DATA_PORT = os.getenv('DATA_PORT', '8000')
FC_URL = os.getenv('FC_URL', '127.0.0.1')
FC_PORT = os.getenv('FC_PORT', '8300')


# def _get_logdata(monitor_name):
#     """ Returned time data is in UTC time unit"""
#     response = requests.get(f'http://{DATA_URL}:{DATA_PORT}/get_logdata?monitor_name={monitor_name}')
#     if response.status_code == 200:
#         return json.loads(response.text)
#     else:
#         return []


def _get_fcdata_bokeh(monitor_name, classes_to_predict=None):
    """Return a dictionary of forecasted values starting with the most recent observation"""
    url = f'http://{FC_URL}:{FC_PORT}/get_forecast?monitor_name={monitor_name}&classes_to_predict={classes_to_predict}' #interval, predictor_hours, from_date
    response = requests.get(url)
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return []


def _get_logdata_bokeh(monitor_name, start_date_utc=None, start_date_utc_gt=None):
    """ Returned data is in UTC time units. Expects time units in UTC. """
    start_field = 'start_date'
    if start_date_utc_gt:
        start_field = 'start_date_gt'
        start_date_utc = start_date_utc_gt
    if start_date_utc is None:
        start_date_utc = '1970-01-01T00:00:00.000000'
    response = requests.get(
        f'http://{DATA_URL}:{DATA_PORT}/get_logdata_bokeh?monitor_name={monitor_name}&{start_field}={start_date_utc}')
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
    # Incoming new value is a tuple of time in epoch format of the video-local timezone
    # attr = 'value_throttled'
    new_start_date = pd.Timestamp(new[0] / 1000, unit='s').tz_localize(TIME_ZONE)
    new_end_date = pd.Timestamp(new[1] / 1000, unit='s').tz_localize(TIME_ZONE)
    _filter_sources(new_start_date, new_end_date)


def toggle_object(attr, old, new):
    # SELECT_OBJECT select widget was changed.
    # Toggle the display of the new value selected
    global DISPLAY_OBJECTS
    if new in DISPLAY_OBJECTS:
        DISPLAY_OBJECTS.remove(new)
    else:
        DISPLAY_OBJECTS.add(new)

    _filter_sources(start_date_utc=min(SOURCE_SCATTER.data['time_stamp_utc']), end_date_utc=max(SOURCE_SCATTER.data['time_stamp_utc']))

    SELECT_OBJECT.value = "show/hide.."


def _update_source_line():
    """ Updates the SOURCE_LINE data source with date in DATA_DF and SOURCE_SCATTER's range"""
    # create SOURCE_LINE data with curves that take previous and next day into account

    # make sure the line uses date ranged from SOURCE_SCATTER so the axes match
    s_time = min(SOURCE_SCATTER.data['time_stamp']) - pd.Timedelta('24 hours')
    e_time = max(SOURCE_SCATTER.data['time_stamp']) + pd.Timedelta('24 hours')

    _source_line_df = DATA_DF[(DATA_DF.time_stamp >= s_time) & (DATA_DF.time_stamp <= e_time) & (DATA_DF.class_name.isin(DISPLAY_OBJECTS))]
    _source_line_df = _source_line_df.pivot_table(index='time_stamp', columns='class_name').fillna(0)

    _xs = (_source_line_df.index - _source_line_df.index.min()).total_seconds().astype(int)
    c_names = list(_source_line_df[('count',)].columns)

    # create a column with the LineaGam values for entire dataset
    n_splines = max(60, int((e_time - s_time).total_seconds() / 60 / 60))
    for c in c_names:
        _source_line_df[('line', c)] = np.clip(
            LinearGAM(s(0, n_splines=n_splines, lam=.6)).fit(_xs, _source_line_df[('count', c)]).predict(_xs), a_min=0,
            a_max=None)

    # now filter the dataset for the time range of the scatter plot that is being presented
    _source_line_df = _source_line_df[(_source_line_df.index >= min(SOURCE_SCATTER.data['time_stamp'])) & (
            _source_line_df.index <= max(SOURCE_SCATTER.data['time_stamp']))]

    SOURCE_LINE.data = {'xs': [sorted(_source_line_df.index) for _ in c_names],
                        'ys': [_source_line_df[('line', c)].values for c in c_names],
                        'line_color': [COLORS.get(c) for c in c_names],
                        'class_names': c_names}


def _filter_sources(start_date_utc=None, end_date_utc=None):
    # change SOURCE_SCATTER so it spans start_date to end_date and include objects
    # dates in UTC timezone
    global DATA_DF, SOURCE_SCATTER

    _data_df = DATA_DF[DATA_DF.class_name.isin(DISPLAY_OBJECTS)]

    if end_date_utc is None and start_date_utc is not None:
        _data_df = _data_df[(_data_df.time_stamp_utc >= start_date_utc)]
    elif end_date_utc is not None and start_date_utc is None:
        _data_df = _data_df[(_data_df.time_stamp_utc <= end_date_utc)]
    elif end_date_utc is not None and start_date_utc is not None:
        _data_df = _data_df[(_data_df.time_stamp_utc >= start_date_utc) & (_data_df.time_stamp_utc <= end_date_utc)]

    # create SOURCE_SCATTER data
    SOURCE_SCATTER.data = _data_df.to_dict(orient='list')

    # update SOURCE_LINE based on DATA_DF and selected range of SOURCE_SCATTER
    _update_source_line()


def get_chart():
    """
    Get a Bokeh chart that shows the trend of detected items recorded in the Log database.
    :param monitor_config:
    :return:
    """
    _filter_sources(start_date_utc=START_DATE_UTC)

    hover_tool = HoverTool(
        tooltips=[
            ("Time", "@time_stamp{%a %m/%d %T}"),
            # https://docs.bokeh.org/en/latest/docs/reference/models/formatters.html#bokeh.models.formatters.DatetimeTickFormatter
            ("Object", "@class_name (@count{0.000})"),
            # ("Rate", '$y'),
            # ("Object", "@class_name")
        ],
        formatters={'@time_stamp': 'datetime'},
        mode='mouse'
    )

    tools = [hover_tool] #, "pan", "wheel_zoom", "zoom_in", "zoom_out", "reset", "tap", "lasso_select", "box_select"]

    # Define the blank canvas of the Bokeh plot that data will be layered on top of
    fig = figure(
        title=f"{MONITOR_NAME}",
        sizing_mode="stretch_both",
        # width_policy="max",
        # height_policy="max",
        tools=tools,
        toolbar_location=None,
        x_axis_type="datetime",
        border_fill_color=None,
        min_border_left=0,
        background_fill_color='lightslategrey',
        background_fill_alpha=.3)

    # Remove default x and y tick marks make chart look clean
    # fig.xgrid.grid_line_color = None
    fig.xaxis.axis_line_color = None
    fig.yaxis.axis_line_color = None
    fig.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
    fig.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
    fig.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
    fig.yaxis.minor_tick_line_color = None  # turn off y-axis minor ticks

    # Hide hours and minutes in the x-axis
    fig.xaxis.formatter = DatetimeTickFormatter(
        days="%a %m/%d",
        months="%m/%Y",
        hourmin="%a %H:%M",
        hours="%H:%M",
        minutes="%a %H:%M",
        seconds="%a %H:%M:%S")
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
    fig.legend.click_policy = 'hide'
    fig.legend.border_line_width = 0
    fig.legend.background_fill_color = "white"
    fig.legend.background_fill_alpha = 0.7

    return fig


@count()
def update(i):
    # i = int representing the number of times this function has been called
    global DATA_DF, LAST_POSTED_TIME_UTC_ISO, COLORS, SOURCE_SCATTER, SOURCE_LINE, DATE_RANGE_SLIDER
    new_raw_data = _get_logdata_bokeh(MONITOR_NAME, start_date_utc_gt=LAST_POSTED_TIME_UTC_ISO)
    if len(new_raw_data) < 1:
        return
    LAST_POSTED_TIME_UTC_ISO = new_raw_data['time_stamp'][-1]

    # UPDATE SOURCE_SCATTER
    new_raw_data_df = pd.DataFrame(new_raw_data)
    new_raw_data_df['time_stamp_utc'] = pd.to_datetime(new_raw_data_df['time_stamp'], utc=True)
    new_raw_data_df['time_stamp'] = new_raw_data_df['time_stamp_utc'].dt.tz_convert(tz=TIME_ZONE.zone).dt.tz_localize(
        None)
    new_raw_data_df['color'] = [COLORS.get(class_name) for class_name in new_raw_data_df['class_name'].values]

    SOURCE_SCATTER.stream(new_raw_data_df.to_dict(orient='list'), rollover=None)  # append new items to source

    # UPDATE THE MASTER DATA_DF
    DATA_DF = DATA_DF.append(new_raw_data_df)

    # UPDATE SOURCE_LINE DATA
    _update_source_line()

    # update the slider end point
    DATE_RANGE_SLIDER.end = DATA_DF['time_stamp'].max()


def update_forecast():
    global DATA_DF, LAST_POSTED_TIME_UTC_ISO, COLORS, SOURCE_SCATTER, SOURCE_LINE, DATE_RANGE_SLIDER
    new_fc_data = _get_fcdata_bokeh(MONITOR_NAME) #, start_date_utc_gt=LAST_POSTED_TIME_UTC_ISO)


args = curdoc().session_context.request.arguments
MONITOR_NAME = None
while MONITOR_NAME is None:
    MONITOR_NAME = args.get('monitor_name')[0].decode()
MONITOR_CONFIG = _get_monitorconfig(MONITOR_NAME)

# if LIMIT is not provided or is 0, there will be no start limit
# if LIMIT is text and is 'true', -14 days will be set as the start limit, else, no limit.
LIMIT_START_DAYS = args.get('limit_start_days')
if LIMIT_START_DAYS is None:
    LIMIT_START_DAYS = 0
else:
    try:
        LIMIT_START_DAYS = int(LIMIT_START_DAYS[0].decode())
        if LIMIT_START_DAYS < 0:
            LIMIT_START_DAYS = 0
    except ValueError:
        if LIMIT_START_DAYS[0].decode().lower() == 'true':
            LIMIT_START_DAYS = 14
        else:
            LIMIT_START_DAYS = 0

TIME_ZONE = None
while TIME_ZONE is None:
    TIME_ZONE = pytz.timezone(MONITOR_CONFIG.get('time_zone'))
    sleep(.1)

print(f"MONITOR NAME: '{MONITOR_CONFIG.get('monitor_name')}' TIME_ZONE: '{MONITOR_CONFIG.get('time_zone')}'")

# SETUP DATA - DATA acts as local master source of all monitor's available data
RAW_DATA = _get_logdata_bokeh(MONITOR_NAME)
DATA_DF = pd.DataFrame(RAW_DATA)
DATA_DF['time_stamp_utc'] = pd.to_datetime(DATA_DF['time_stamp'], utc=True)
DATA_DF['time_stamp'] = DATA_DF['time_stamp_utc'].dt.tz_convert(tz=TIME_ZONE.zone).dt.tz_localize(None)
LAST_POSTED_TIME_UTC_ISO = RAW_DATA['time_stamp'][-1]
COLORS = json.loads(requests.get(
    f'http://{DATA_URL}:{DATA_PORT}/get_monitor?monitor_name={MONITOR_NAME}&field=class_colors').text)[
    'class_colors']
COLORS = {k: RGB(*c) for k, c in COLORS.items()}
DATA_DF['color'] = [COLORS.get(class_name) for class_name in DATA_DF['class_name'].values]

try:
    # we expect the start date to be in the monitor's timezone - convert it to UTC
    START_DATE_UTC = args.get('start_date')[0].decode()
    # If time was provided with a time zone indicator at the end, remove it - assumes UTC time
    while START_DATE_UTC[-1].isalpha():
        START_DATE_UTC = START_DATE_UTC[:-1]
    START_DATE_UTC = datetime.fromisoformat(START_DATE_UTC).replace(tzinfo=TIME_ZONE).astimezone(pytz.UTC)
except:
    START_DATE_UTC = DATA_DF['time_stamp_utc'].min()

DISPLAY_OBJECTS = set(DATA_DF['class_name'].unique())

# SETUP FC_DATA - this acts as a local master source of the current FC
RAW_FC = _get_fcdata_bokeh(MONITOR_NAME)
FC_DF = pd.DataFrame(RAW_FC)
FC_DF['color'] = [COLORS.get(class_name) for class_name in FC_DF['class_name'].values]


# setup data sources for plots
SOURCE_SCATTER = ColumnDataSource(data={})
SOURCE_LINE = ColumnDataSource(data={})

# setup widgets
# WIDGET: DATE_RANGE_SLIDER
start_limit = DATA_DF['time_stamp'].min()
if LIMIT_START_DAYS:
    start_limit = max(DATA_DF['time_stamp'].min(), DATA_DF['time_stamp'].max() - pd.Timedelta(f'{LIMIT_START_DAYS} days'))

DATE_RANGE_SLIDER = DateRangeSlider(value=(START_DATE_UTC.astimezone(TIME_ZONE), DATA_DF['time_stamp'].max()),
                                    start=start_limit,
                                    end=DATA_DF['time_stamp'].max(), step=6, height_policy="min",
                                    margin=(0, 0, 0, 0), show_value=True, width_policy="max")
DATE_RANGE_SLIDER.on_change("value_throttled", change_date)

# WIDGET: SELECT_OBJECT
SELECT_OBJECT = Select(value="show/hide..",
                       options=["show/hide.."] + list(DATA_DF['class_name'].unique()),
                       margin=(10, 0, 0, 0))
SELECT_OBJECT.on_change("value", toggle_object)
# SELECT_OBJECT.js_on_change("value", CustomJS(code=""" console.log(cb_obj.value); """))

if MONITOR_NAME:
    curdoc().add_root(column(row(DATE_RANGE_SLIDER, Spacer(width=30), SELECT_OBJECT), get_chart()))
    curdoc().add_periodic_callback(update, 30000)  # 30000 = 30seconds
    curdoc().title = f"{MONITOR_NAME}"
