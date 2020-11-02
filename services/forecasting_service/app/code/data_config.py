#  This module contains scripts used to support the forecasting process
import logging
import pytz
import datetime

import pandas as pd
import numpy as np

from ..models.models import TrafficMonitorLogentry as LogEntry
from ..models.models import TrafficMonitorMonitor as Monitor

logger = logging.getLogger("model_logger")
logger.setLevel(logging.INFO)


class DataConfig:
    # Use Pandas Timestamp for datetime to ensure DST conversions are consistent
    def __init__(self, monitor_name: str, interval: int, hours_in_training: int,
                 hours_in_prediction: int, string_predictor_columns: list = None,
                 full_predictor_columns: list = None, response_columns: list = None,
                 source_data_from_date: str = None):
        if string_predictor_columns is None:
            string_predictor_columns = ['class_code']
        if response_columns is None:
            response_columns = ['rate']
        self.monitor_name: str = monitor_name
        self.time_zone = Monitor.objects.get(pk=self.monitor_name).feed.time_zone
        self.interval: int = interval
        self.hours_in_training: int = hours_in_training
        self.hours_in_prediction: int = hours_in_prediction
        self.string_predictor_columns = string_predictor_columns
        self.predictor_columns = full_predictor_columns
        self.response_columns = response_columns
        self.from_date_utc = None if source_data_from_date is None else pd.Timestamp(source_data_from_date,
                                                                                     tz=self.time_zone).tz_convert(pytz.UTC)
        self.categories: list = Monitor.objects.get(pk=self.monitor_name).log_objects
        self.full_df: pd.DataFrame = None
        self.train_df: pd.DataFrame = None
        self.test_df: pd.DataFrame = None
        self.cat_to_code_map: dict = {c: i for i, c in enumerate(self.categories)}
        self.code_to_cat_map: dict = {v: k for k, v in self.cat_to_code_map.items()}

        #         self._set_dates()
        #         self._set_full_df()
        #         self._set_train_test_split()
        self.update_data()
        if self.predictor_columns is None:
            self._set_predictor_columns()

    def __str__(self):
        source_data_from_date = self.from_date_utc.tz_convert(pytz.timezone(self.time_zone)).replace(
            tzinfo=None).isoformat()
        print_params = {'monitor_name': self.monitor_name,
                        'interval': self.interval,
                        'hours_in_training': self.hours_in_training,
                        'hours_in_prediction': self.hours_in_prediction,
                        'string_predictor_columns': self.string_predictor_columns,
                        #                        'full_predictor_columns': self.predictor_columns,
                        'response_columns': self.response_columns,
                        'source_data_from_date': source_data_from_date}
        rv = ''
        for k, v in print_params.items():
            rv += f"{k:25}: {v}\n"
        return rv

    def update_data(self):
        self._set_dates()
        self._set_full_df()
        self._set_train_test_split()

    def get_code(self, category_name: str):
        return self.cat_to_code_map.get(category_name)

    def get_category(self, category_code: int):
        return self.code_to_cat_map.get(category_code)

    def _set_dates(self):
        if self.from_date_utc is None:
            self.from_date_utc = pd.Timestamp(
                LogEntry.objects.filter(monitor=self.monitor_name).earliest('time_stamp').time_stamp)

    def _get_logdata_df(self, from_date=None):
        # times returned are in UTC
        _filter_args = {'monitor_id': self.monitor_name}
        _filter_args.update({'class_name__in': self.categories})
        if from_date is None:
            _filter_args.update({'time_stamp__gte': self.from_date_utc})
        else:
            _filter_args.update({'time_stamp__gte': from_date})
        _df = pd.DataFrame(LogEntry.objects.filter(**_filter_args).all().values())

        if len(_df) == 0:
            raise Exception(
                f"No records returned: monitor:{self.monitor_name} from_date:{self.from_date_utc if from_date is None else from_date} categories:{self.categories}")

        # save the UTC times
        _df.insert(1, 'time_stamp_utc', _df['time_stamp'])
        # _df['time_stamp_utc'] = _df['time_stamp'].dt

        # convert time to monitor's timezone
        _df['time_stamp'] = _df['time_stamp'].dt.tz_convert(pytz.timezone(self.time_zone))
        return _df

    def _set_train_test_split(self):
        split_time = self.full_df.time_stamp.max() - pd.Timedelta(f"{self.hours_in_prediction + 1} hours")
        self.train_df = self.full_df[self.full_df.time_stamp < split_time]
        self.test_df = self.full_df[self.full_df.time_stamp >= split_time]

    def get_train_test_split(self):
        if self.train_df is None or self.test_df is None:
            self._set_train_test_split()

        _tr_x = self.train_df[self.predictor_columns].reset_index(drop=True)
        _te_x = self.test_df[self.predictor_columns].reset_index(drop=True)
        _tr_y = self.train_df[self.response_columns].reset_index(drop=True).to_numpy()
        _te_y = self.test_df[self.response_columns].reset_index(drop=True).to_numpy()

        # reshape single y columns
        if len(_tr_y.shape) > 1 and _tr_y.shape[1] == 1:
            _tr_y = _tr_y.reshape(-1)
        if len(_te_y.shape) > 1 and _te_y.shape[1] == 1:
            _te_y = _te_y.reshape(-1)

        return _tr_x, _tr_y, _te_x, _te_y

    def get_full_prediction_set(self):
        X = self.full_df[self.predictor_columns].reset_index(drop=True)
        y = self.full_df[self.response_columns].reset_index(drop=True)
        return X, y

    def _set_predictor_columns(self):
        """ Adds the history columns to a provided list of columns """
        self.predictor_columns = self.string_predictor_columns + [c for c in self.full_df.columns if c.startswith('-')][
                                                                 ::-1]

    def _set_interval(self, _df: pd.DataFrame, interval: int):
        """ Takes raw DF from Django call the LogEntry.objects.all().values() """
        """ 'interval' must divide hour into equal portions; 60, 30, 15, 10, 6, 4, 3, 2, 1"""
        if 60 % interval != 0:
            logger.error("Interval must be evenly divided into 60: (60, 30, 15, 10, 6, 4, 3, 2 or 1)")

        _df.rename(columns={'count': 'rate'}, inplace=True)

        # make columns categorical and remove multi_index
        # _df = _df.pivot_table(index=['time_stamp'], columns='class_name', values='rate', fill_value=0)
        _df = _df.pivot_table(index=['time_stamp_utc'], columns='class_name', values='rate', fill_value=0)

        _df.columns = _df.columns.get_level_values(0).values
        _df['year'] = pd.Series(_df.index).apply(lambda s: s.year).values
        _df['month'] = pd.Series(_df.index).apply(lambda s: s.month).values
        _df['day'] = pd.Series(_df.index).apply(lambda s: s.day).values
        _df['hour'] = pd.Series(_df.index).apply(lambda s: s.hour).values
        _df['interval'] = pd.Series(_df.index).apply(lambda s: int(s.minute / interval) * interval).values

        _df = _df.groupby(['year', 'month', 'day', 'hour', 'interval']).mean()

        # reconfigure index to a timestamp in UTC
        _df.set_index(pd.Series(list(_df.index)).apply(lambda s: datetime.datetime(*s, tzinfo=pytz.UTC)), inplace=True)

        # complete interval sequence
        start_time = _df.index.min()
        end_time = _df.index.max()
        new_interval = []
        t = start_time
        while t <= end_time:
            new_interval.append(t)
            t += pd.Timedelta(f"{interval} minutes")

        _df = pd.DataFrame(index=new_interval).join(_df, how='outer')

        # fill missing time intervals for forward filling the first half and backfilling the second half
        while _df.isna().any().any():
            _df.fillna(method='ffill', limit=1, inplace=True)
            _df.fillna(method='bfill', limit=1, inplace=True)

        _df = _df.melt(ignore_index=False, var_name='class_name', value_name='rate')

        _df = _df.reset_index().rename(columns={'index': 'time_stamp'})

        return _df

    def _add_categorical_column(self, _df, cat_col_name, code_col_name):
        idx = int(np.where(_df.columns == cat_col_name)[0][0])
        _df.insert(idx + 1, code_col_name, _df[cat_col_name].apply(lambda s: self.get_code(s)))
        return _df

    @staticmethod
    def add_time_features(_df: pd.DataFrame):
        """ add time characteristics that allow grouping """
        _df['year'] = pd.Series(_df.time_stamp).apply(lambda s: s.year).values
        _df['month'] = pd.Series(_df.time_stamp).apply(lambda s: s.month).values
        _df['day'] = pd.Series(_df.time_stamp).apply(lambda s: s.day).values
        _df['weekday'] = pd.Series(_df.time_stamp).apply(lambda s: s.weekday()).values
        _df['hour'] = pd.Series(_df.time_stamp).apply(lambda s: s.hour).values
        _df['minute'] = pd.Series(_df.time_stamp).apply(lambda s: s.minute).values
        _df['day_minute'] = pd.Series(_df.time_stamp).apply(lambda s: (s.hour * 60 + s.minute)).values
        _df['week_minute'] = pd.Series(_df.time_stamp).apply(
            lambda s: (s.weekday() * 24 * 60) + (s.hour * 60) + s.minute).values

        return _df

    def _add_history_columns(self, _df):
        # history columns are added to training datasets
        # value_column is the column to get the history for
        # n_intervals are the number of history columns to add
        categories = _df['class_name'].unique()
        n_intervals = self.hours_in_training * int(60 / self.interval)
        for i in range(1, n_intervals + 1):
            for c in categories:
                idx = _df.loc[_df['class_name'] == c].index
                _df.loc[idx, f'-{i}'] = _df[_df['class_name'] == c]['rate'].shift(i)
        _df.dropna(inplace=True)
        return _df.reset_index(drop=True)

    def _set_full_df(self):
        _df = self._get_logdata_df()
        _df = self._set_interval(_df, interval=self.interval)
        _df = self._add_categorical_column(_df, 'class_name', 'class_code')
        _df = self.add_time_features(_df)
        _df = self._add_history_columns(_df)

        self.full_df = _df  # times are tz aware in UTC

    def get_seed_observation(self, on_date='latest'):
        # get the most recent observation or the first observation on a provided date
        # provided as from_date (is isoformat YYYY-MM_DDTHH:MM)
        # on_date is expected to be in the monitor's timezone

        # first, refresh the full set of data on which to base the forecast
        self._set_full_df()

        if on_date == 'latest' or on_date is None:
            on_date = self.full_df.time_stamp.max()
        else:
            on_date = pd.Timestamp(on_date)
            on_date = self.full_df.time_stamp[self.full_df.time_stamp >= on_date].min()

        _df = self.full_df[self.full_df.time_stamp == on_date]
        time_zero = _df['rate'].values

        # only keep the predictor columns
        _df = _df.reset_index(drop=True)[self.predictor_columns]
        _df["0"] = time_zero

        if len(_df) == 0:
            raise Exception(
                f"Unable to get forecasting seed: monitor:{self.monitor_name}, interval:{self.interval}, hours_in_prediction:{self.hours_in_prediction}, on_date:{on_date}, categories:{self.categories}")

        return _df, on_date
