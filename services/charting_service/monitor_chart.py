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
from bokeh.models import ColumnDataSource, DateRangeSlider, Select, Spacer, Dropdown
from bokeh.driving import count
from bokeh.layouts import column, row
from bokeh.server.views import ws

logging.basicConfig(level=logging.INFO)

APP_HOST = os.getenv('APP_HOST', '127.0.0.1')
APP_PORT = os.getenv('APP_PORT', '8000')
FC_HOST = os.getenv('FC_HOST', '127.0.0.1')
FC_PORT = os.getenv('FC_PORT', '8200')


def _get_logdata(monitor_name, start_date_utc=None, start_date_utc_gt=None):
    """ Returned data is in UTC time units. Expects time units in UTC. """
    start_field = 'start_date'
    if start_date_utc_gt:
        start_field = 'start_date_gt'
        start_date_utc = start_date_utc_gt
    if start_date_utc is None:
        start_date_utc = '1970-01-01T00:00:00.000000'
    try:
        response = requests.get(
            f'http://{APP_HOST}:{APP_PORT}/get_logdata_bokeh?monitor_name={monitor_name}&{start_field}={start_date_utc}')
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return {}
    except ConnectionRefusedError as e:
        terminate(4)
    except ConnectionError as e:
        terminate(3)


def get_chart():
    """
    Get a Bokeh chart that shows the trend of detected items recorded in the Log database.
    :return:
    """

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

    tools = [hover_tool]  # , "pan", "wheel_zoom", "zoom_in", "zoom_out", "reset", "tap", "lasso_select", "box_select"]

    # Define the blank canvas of the Bokeh plot that data will be layered on top of
    fig = figure(
        title=f"{monitor_config.name}",
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
    fig.xaxis.axis_label = display_data.time_zone.zone

    # CREATE SCATTER PLOTS
    fig.scatter(x='time_stamp', y='count',
                fill_color='color',
                legend_field='class_name',
                line_color='black',
                size=3, alpha=.5, line_width=.3,
                source=display_data.source_act_scatter)

    # make a source just for the legend
    # fig.scatter(fill_color='color', legend_field='class_name', line_color='black',
    #             size=3, alpha=.5, line_width=.3, source=SOURCE_LEGEND)

    # CREATE LINE PLOTS FOR ACTUAL DATA
    fig.multi_line(xs='xs', ys='ys',
                   line_color='line_color',
                   line_width=3,
                   source=display_data.source_act_line)

    # CREATE LINE PLOTS FOR FC DATA
    fig.multi_line(xs='xs', ys='ys',
                   line_color='line_color',
                   line_width=3,
                   line_dash='dotted',  # solid, dashed, dotted, dotdash, dashdot
                   source=display_data.source_fc_line)

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
    """ Called periodically by the server loop. """
    # i = int representing the number of times this function has been called
    # global SOURCE_ACT_SCATTER, SOURCE_ACT_LINE #, DATE_RANGE_SLIDER
    new_raw_data = _get_logdata(monitor_config.name, start_date_utc_gt=display_data.last_posted_time_utc_iso)
    if len(new_raw_data) < 1:
        return
    display_data.last_posted_time_utc_iso = new_raw_data['time_stamp'][-1]

    # UPDATE SOURCE_ACT_SCATTER - add the scatter points for the new data
    new_raw_data_df = pd.DataFrame(new_raw_data)
    new_raw_data_df['time_stamp_utc'] = pd.to_datetime(new_raw_data_df['time_stamp'], utc=True)
    new_raw_data_df['time_stamp'] = new_raw_data_df['time_stamp_utc'].dt.tz_convert(
        tz=monitor_config.time_zone.zone).dt.tz_localize(
        None)
    new_raw_data_df['color'] = [class_colors.colors.get(class_name) for class_name in
                                new_raw_data_df['class_name'].values]

    display_data.add_data_point(new_raw_data_df)  # .to_dict(orient='list'))


class MonitorConfig:
    def __init__(self, arg_dict: dict):
        self.name = arg_dict.get('monitor_name', None)
        self.config = self._get_config()
        tz = None
        while tz is None:
            try:
                tz = pytz.timezone(self.config.get('time_zone'))
            except:
                sleep(.1)
        self.time_zone = tz

    def _get_config(self):
        response = requests.get(f'http://{APP_HOST}:{APP_PORT}/get_monitor?monitor_name={self.name}')
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return None


class ClassColors:
    """ Holds class color mappings """

    def __init__(self, monitor: MonitorConfig):
        self.monitor_name = monitor.name
        self.colors = self._get_colors()

    def _get_colors(self):
        colors = json.loads(requests.get(
            f'http://{APP_HOST}:{APP_PORT}/get_monitor?monitor_name={self.monitor_name}&field=class_colors').text)[
            'class_colors']
        colors = {k: RGB(*c) for k, c in colors.items()}

        return colors


class ForecastGenerator:
    """ Holds the parameters used when creating forecasts """

    def __init__(self, monitor: MonitorConfig, arg_dict: dict):
        self.monitor_name = monitor.name
        self.time_zone = monitor.time_zone
        self.interval = arg_dict.get('interval', None)
        self.hours_in_training = arg_dict.get('hours_in_training', None)
        self.hours_in_prediction = arg_dict.get('hours_in_prediction', None)
        self.source_data_from_date = arg_dict.get('fc_source_data_from_date', None)

    def retrain_all(self):
        url = f'http://{FC_HOST}:{FC_PORT}/retrain_all?monitor_name={self.monitor_name}'

    def _get_fcdata(self, interval=None, hours_in_training=None, hours_in_prediction=None,
                    source_data_from_date=None):
        """Return a dictionary of forecasted values starting with the most recent observation"""
        url_params = {'interval': interval,
                      'hours_in_training': hours_in_training,
                      'hours_in_prediction': hours_in_prediction,
                      # 'source_data_from_date': source_data_from_date
                      }
        url = f'http://{FC_HOST}:{FC_PORT}/predict?monitor_name={self.monitor_name}'

        for p, v in url_params.items():
            if v is not None:
                url += f"&{p}={v}"

        response = requests.get(url)
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            print(f"URL ERROR {response.status_code}")
            return []

    def get_models(self):
        url = f'http://{FC_HOST}:{FC_PORT}/get_available_models?monitor_name={self.monitor_name}'
        response = requests.get(url)
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            print(f"URL ERROR {response.status_code}")
            return {}

    def get_model(self, filename):
        url = f'http://{FC_HOST}:{FC_PORT}/get_model?filename={filename}'
        response = requests.get(url)
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            print(f"URL ERROR {response.status_code}")
            return {}

    def get_fc(self, interval=None,
               hours_in_training=None,
               hours_in_prediction=None):
        if interval is None:
            interval = self.interval
        if hours_in_training is None:
            hours_in_training = self.hours_in_training
        if hours_in_prediction is None:
            hours_in_prediction = self.hours_in_prediction
        # if source_data_from_date is None:
        #     source_data_from_date = self.source_data_from_date

        preds = self._get_fcdata(interval=interval,
                                 hours_in_training=hours_in_training,
                                 hours_in_prediction=hours_in_prediction,
                                 # source_data_from_date=source_data_from_date
                                 )

        if len(preds) == 0:
            return None

        rv_df = pd.DataFrame(preds)  # in UTC timezone

        # data is predicted in UTC - convert to tz-unaware times in monitor's local time
        rv_df['time_stamp'] = [pd.Timestamp(t) for t in rv_df['time_stamp'].values]
        rv_df['time_stamp'] = rv_df['time_stamp'].dt.tz_convert(tz=self.time_zone).dt.tz_localize(tz=None)

        return rv_df


class DisplayData:
    """ Holds currently displayed data sources """

    def __init__(self, monitor: MonitorConfig, fc: ForecastGenerator,
                 colors: ClassColors, arg_dict: dict):

        self.monitor_name = monitor.name
        self.time_zone = monitor.time_zone
        self.colors = colors.colors

        # set available range of data - data set may be years long, so we cap this
        limit = int(arg_dict.get('limit_start_days', 14))
        self.start_available_range_utc = pd.Timestamp.now(tz=pytz.UTC) - pd.Timedelta(f'{limit} days')
        self.start_available_range = self.start_available_range_utc.astimezone(pytz.UTC).tz_convert(
            self.time_zone).tz_localize(None)

        # Set dataframes that contain the full range of data and the displayed range of data
        _df = pd.DataFrame(_get_logdata(self.monitor_name, start_date_utc_gt=self.start_available_range_utc))
        _df['time_stamp_utc'] = pd.to_datetime(_df['time_stamp'], utc=True)
        _df['time_stamp'] = _df['time_stamp_utc'].dt.tz_convert(tz=self.time_zone).dt.tz_localize(None)
        _df['color'] = [self.colors.get(class_name) for class_name in _df['class_name'].values]
        self.full_act_df: pd.DataFrame = _df

        # We will choose to display a subset of the data available
        # The user can still use a slider to extend the range
        start_display = arg_dict.get('start_date', self.full_act_df['time_stamp'].min().isoformat())
        # If time was provided with a time zone indicator at the end, remove it
        while start_display[-1].isalpha():
            start_display = start_display[:-1]
        self.start_display_range: pd.Timestamp = pd.Timestamp(
            datetime.fromisoformat(start_display).replace(tzinfo=None))

        # Based on the full and displayed dataframe ranges, determine that available objects and the ones displayed
        self.available_classes = set(self.full_act_df['class_name'].unique())
        self.displayed_classes = set(self.full_act_df['class_name'].unique())

        # Generate a forecast - this is based on the most recently observed values by the monitor
        self.fc_generator = fc
        self.fc_args = {}
        fc_keys = ['hours_in_training', 'hours_in_prediction', 'interval']
        for k, v in arg_dict.items():
            if k in fc_keys:
                self.fc_args.update({k: v})

        self.full_fc_df: pd.DataFrame = self.fc_generator.get_fc(**self.fc_args)

        self.end_available_range = self.full_fc_df.time_stamp.max()
        self.end_display_range: pd.Timestamp = pd.Timestamp(self.end_available_range)

        self.last_posted_time_utc_iso = max(self.full_act_df['time_stamp_utc']).isoformat()

        self.source_act_scatter = ColumnDataSource(data={})
        self.source_act_line = ColumnDataSource(data={})
        self.source_fc_line = ColumnDataSource(data={})

        self.update_sources()

    def add_data_point(self, points_df: pd.DataFrame):

        # append new items to source
        display_data.source_act_scatter.stream(points_df.to_dict(orient='list'), rollover=None)

        # UPDATE THE MASTER DATA_DF
        self.full_act_df = self.full_act_df.append(points_df, sort=False)

        # UPDATE SOURCE_ACT_LINE DATA
        self.set_source_act_scatter()
        self.set_source_act_line()

        # update the slider end point
        # chart_config.date_range_slider.end = chart_config.data_df['time_stamp'].max()

    def update_sources(self):
        self.set_source_act_scatter()
        self.set_source_act_line()
        self.set_source_fc_line()

    def set_source_act_scatter(self):
        _df = self.full_act_df[(self.full_act_df.time_stamp >= self.start_display_range) &
                               (self.full_act_df.time_stamp <= self.end_display_range) &
                               (self.full_act_df.class_name.isin(self.displayed_classes))]
        self.source_act_scatter.data = _df.to_dict(orient='list')

    def set_source_act_line(self):
        # This is complex because we need to create reasonably smooth lines at the ends of the interval

        # we temporarily extend _source_line_df to calculate the smoothed GAM lines
        s_time: pd.Timestamp = max(self.start_display_range - pd.Timedelta('24 hours'),
                                   min(self.full_act_df.time_stamp))
        e_time: pd.Timestamp = min(self.end_display_range + pd.Timedelta('24 hours'), max(self.full_act_df.time_stamp))

        _source_line_df = self.full_act_df[
            (self.full_act_df.time_stamp >= s_time) & (self.full_act_df.time_stamp <= e_time) & (
                self.full_act_df.class_name.isin(self.displayed_classes))]

        # append future forecast points to _source_line_df if relevant
        _fc_to_append_df = self.full_fc_df[(self.full_fc_df.time_stamp > max(_source_line_df.time_stamp)) & (
                self.full_fc_df.time_stamp < e_time)]  # fc points beyond the actual data

        _source_line_df = _source_line_df.append(_fc_to_append_df, ignore_index=True, sort=False)

        # pivot the data to make subsequent data handling easier
        _source_line_df = _source_line_df.pivot_table(index='time_stamp', columns='class_name').fillna(0)

        # get a list of the class names to be plotted
        c_names = list(_source_line_df[('count',)].columns)

        # create a column with the LineaGam values for a time period before and after what
        # is displayed so the lines are smooth at the ends
        # convert times to integers for linearGAM line creation
        _xs = (_source_line_df.index - _source_line_df.index.min()).total_seconds().astype(int)
        n_splines = max(60, int((e_time - s_time).total_seconds() / 60 / 60))
        for c in c_names:
            _source_line_df[('line', c)] = np.clip(
                LinearGAM(s(0, n_splines=n_splines, lam=.6)).fit(_xs, _source_line_df[('count', c)]).predict(_xs),
                a_min=0,
                a_max=None)

        # We extended the range of the data so that the end of the GAM lines reflect
        # data outside the displayed range of the chart.
        # We now, limit the range of the data to actually be plotted.
        _source_line_df = _source_line_df[
            (_source_line_df.index >= self.start_display_range) & (_source_line_df.index <= self.end_display_range)]

        if len(_source_line_df) == 0:
            self.source_act_line.data = {}
        else:
            self.source_act_line.data = {'xs': [sorted(_source_line_df.index) for _ in c_names],
                                         'ys': [_source_line_df[('line', c)].values for c in c_names],
                                         'line_color': [class_colors.colors.get(c) for c in c_names],
                                         'class_name': c_names}

    def set_source_fc_line(self):

        _fc_line_df = self.full_fc_df[
            (self.full_fc_df.class_name.isin(self.displayed_classes)) & (
                    self.full_fc_df.time_stamp >= self.start_display_range) & (
                    self.full_fc_df.time_stamp <= self.end_display_range)]
        _fc_line_df = _fc_line_df.pivot_table(index='time_stamp', columns='class_name').fillna(0)

        if len(_fc_line_df) == 0:
            data = {}
        else:
            # get a list of the class names to be plotted
            c_names = list(_fc_line_df[('count',)].columns)

            data = {'xs': [sorted(_fc_line_df.index) for _ in c_names],
                    'ys': [_fc_line_df[('count', c)].values for c in c_names],
                    'line_color': [class_colors.colors.get(c) for c in c_names],
                    'class_name': c_names}

        self.source_fc_line.data = data

    def change_fc_model(self, filename):
        m = list(self.fc_generator.get_model(filename).values())[0]
        self.fc_args = {'interval': m['interval'],
                        'hours_in_training': m['hours_in_training'],
                        'hours_in_prediction': m['hours_in_prediction']}
        self.update_fc_and_redraw()

    def update_fc(self):
        _fc_df = self.fc_generator.get_fc(**self.fc_args)
        self.full_fc_df = _fc_df
        self.end_available_range = self.full_fc_df.time_stamp.max()
        self.end_display_range = self.full_fc_df.time_stamp.max()

    def update_fc_and_redraw(self):
        self.update_fc()
        self.set_source_fc_line()

    def change_displayed_date_range(self, start_date=None, end_date=None):
        """ Update the displayed_act_df and displayed_fc_df for date range supplied """
        self.start_display_range = start_date
        self.end_display_range = end_date
        self.update_sources()


class Widgets:
    """ Defines and manages widgets used to control charted data """

    def __init__(self, data: DisplayData):
        self.data = data

        self.date_range_slider = DateRangeSlider(
            value=(data.start_display_range, data.end_display_range),
            start=data.start_available_range, end=data.end_available_range,
            step=6,
            # height_policy="min",
            margin=(0, 0, 0, 0),
            show_value=True,
            width=200, height=25,
            sizing_mode='fixed')
        self.date_range_slider.on_change("value_throttled", self._change_date)

        self.select_object = Select(value="show/hide..",
                                    width=200, height=25,
                                    sizing_mode='fixed',
                                    options=self.get_select_options(),
                                    margin=(8, 0, 0, 0))
        self.select_object.on_change("value", self.toggle_object)

        models = self.data.fc_generator.get_models()
        menu = [(f"IntMins:{p['interval']:>3} | Train:{p['hours_in_training']:>4} | Pred:{p['hours_in_prediction']:>3} | {round(float(p['score']),2)}", k) for k, p in models.items()]
        self.dropdown_selfc = Dropdown(label="Select FC Model",
                                       button_type='primary',
                                       menu=menu,
                                       width=200, height=30,
                                       sizing_mode='fixed',
                                       margin=(8, 0, 0, 0))
        self.dropdown_selfc.on_event("menu_item_click", self._update_fc)
                                     # lambda e: self.data.change_fc_model(e.item))#,
                                     # lambda e: self._update_slider_dates)

    def get_select_options(self):
        return list(["show/hide.."]) + sorted(list(self.data.available_classes))

    def _update_fc(self, e):
        self.data.change_fc_model(e.item)
        self._update_slider_dates()

    def _update_slider_dates(self):
        self.date_range_slider.value = (self.data.start_display_range, self.data.end_display_range)
        self.date_range_slider.start = self.data.start_available_range
        self.date_range_slider.end = self.data.end_available_range

    def _change_date(self, attr, old, new):
        # Incoming new value is a tuple of time in epoch format of the video-local timezone
        # attr = 'value_throttled'
        new_start_date = pd.Timestamp(new[0] / 1000, unit='s')  # .tz_localize(TIME_ZONE)
        new_end_date = pd.Timestamp(new[1] / 1000, unit='s')  # .tz_localize(TIME_ZONE)
        self.data.change_displayed_date_range(new_start_date, new_end_date)

    def toggle_object(self, attr, old, new):
        # SELECT_OBJECT select widget was changed.
        # Toggle the display of the new value selected
        if new in self.data.displayed_classes:
            self.data.displayed_classes.remove(new)
        else:
            self.data.displayed_classes.add(new)
        self.select_object.value = "show/hide.."

        # redraw the sources with the new values in displayed_objects
        self.data.update_sources()


# CB_ID = None

@count()
def retrain_daily(i):
    """ Sets a callback that will retrain all models at midnight local time """
    # global CB_ID
    tinfo = requests.get("https://ipapi.co/json/").json()
    logging.info(tinfo)
    if tinfo.get('timezone', None) is not None:
        tz = tinfo['timezone']
        local_time = datetime.now(tz=pytz.timezone(tz))
        tmrw = (local_time + timedelta(days=1)).date()
        midnight = datetime(year=tmrw.year, month=tmrw.month, day=tmrw.day).replace(tzinfo=pytz.timezone(tz))
        secs_to_midnight = (midnight - local_time).seconds
        # if CB_ID is not None:
        if i:
            # curdoc().remove_timeout_callback(CB_ID)
            fc_generator.retrain_all()
        curdoc().add_timeout_callback(retrain_daily, secs_to_midnight * 1000)


def terminate(code: int = 99):
    codes = {0: "Normal termination",
             1: "Websocket Closed",
             2: "Connection Error",
             3: "Connection Refused",
             99: "Unknown Failure"}
    logging.error(f"Application Terminated: {code}-{codes.get(code, 99)}")
    exit(code)


# PARSE THE URL ARGUMENTS
args = curdoc().session_context.request.arguments
args = {k: v[0].decode() for k, v in args.items()}  # convert from binary lists

# Create components of chart
monitor_config: MonitorConfig = MonitorConfig(arg_dict=args)
fc_generator: ForecastGenerator = ForecastGenerator(monitor=monitor_config, arg_dict=args)
class_colors = ClassColors(monitor=monitor_config)
display_data = DisplayData(monitor=monitor_config,
                           fc=fc_generator,
                           colors=class_colors, arg_dict=args)
widgets = Widgets(display_data)


# exit codes: 1-websocket closed, 2-curdoc loop failed, 3-connection error
ws.WSHandler.on_close = lambda x: terminate(1)

# build page
try:

    curdoc().add_root(
        column(row(widgets.date_range_slider, Spacer(width=15), widgets.select_object, Spacer(width=15),
                   widgets.dropdown_selfc), get_chart()))
    curdoc().add_periodic_callback(update, 30 * 1000)  # 30000 = 30seconds
    curdoc().add_periodic_callback(display_data.update_fc_and_redraw, 60 * 60 * 24 * 1000)  # 1x daily
    retrain_daily()  # setup callback to retrain all models at midnight each day
    curdoc().title = f"{monitor_config.name}"
except:
    terminate(2)
