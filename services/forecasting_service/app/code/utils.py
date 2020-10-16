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


def get_rs(monitor_name, categories, from_date: str):
    # date should be in ISO format YYYY-MM-DDTHH:MM
    from_date = datetime.datetime.fromisoformat(from_date).replace(tzinfo=pytz.UTC)
    return LogEntry.objects.filter(monitor_id=monitor_name, class_name__in=categories, time_stamp__gte=from_date).all().values()


def set_interval(_df: pd.DataFrame, interval: int):
    """ Takes raw DF from Django call the LogEntry.objects.all().values() """
    """ 'interval' must divide hour into equal portions; 60, 30, 15, 10, 6, 4, 3, 2, 1"""
    if 60 % interval != 0:
        logger.error("Interval must be evenly divided into 60: (60, 30, 15, 10, 6, 4, 3, 2 or 1)")
    monitor_name: str = _df.monitor_id.unique()[0]
    time_zone = Monitor.objects.get(pk=monitor_name).feed.time_zone

    _df.rename(columns={'count': 'rate'}, inplace=True)

    # convert time to video local timezone and then remove timezone awareness
    _df['time_stamp'] = _df['time_stamp'].dt.tz_convert(pytz.timezone(time_zone)).dt.tz_localize(None)

    # make columns categorical and remove multi_index
    _df = _df.pivot_table(index=['time_stamp'], columns='class_name', values='rate', fill_value=0)

    _df.columns = _df.columns.get_level_values(0).values
    _df['year'] = pd.Series(_df.index).apply(lambda s: s.year).values
    _df['month'] = pd.Series(_df.index).apply(lambda s: s.month).values
    _df['day'] = pd.Series(_df.index).apply(lambda s: s.day).values
    _df['hour'] = pd.Series(_df.index).apply(lambda s: s.hour).values
    _df['interval'] = pd.Series(_df.index).apply(lambda s: int(s.minute / interval) * interval).values

    _df = _df.groupby(['year', 'month', 'day', 'hour', 'interval']).mean()
    # reconfigure index to a timestamp
    _df.set_index(pd.Series(list(_df.index)).apply(lambda s: datetime.datetime(*s)), inplace=True)

    # complete interval sequence so there are no gaps
    start_time = _df.index.min()
    end_time = _df.index.max()
    new_interval = []
    t = start_time
    while t <= end_time:
        new_interval.append(t)
        t += pd.Timedelta(f"{interval} minutes")

    _df = pd.DataFrame(index=new_interval).join(_df, how='outer')

    # fill missing time intervals for forward-filling the first half and back-filling the second half
    while _df.isna().any().any():
        _df.fillna(method='ffill', limit=1, inplace=True)
        _df.fillna(method='bfill', limit=1, inplace=True)

    _df = _df.melt(ignore_index=False, var_name='class_name', value_name='rate')

    return _df.reset_index().rename(columns={'index': 'time_stamp'})


def add_category_codes(_df, column_to_cat, new_col_name):
    # Use numerical category codes
    idx = int(np.where(_df.columns == column_to_cat)[0][0])
    _df[column_to_cat] = pd.Categorical(_df[column_to_cat])
    _df.insert(idx + 1, new_col_name, _df[column_to_cat].cat.codes)

    return _df


def get_cat_map(_df, string_column, code_column) -> dict:
    _cat_map_name_to_code = _df[[string_column, code_column]].set_index(string_column).drop_duplicates().to_dict()[code_column]
    _cat_map_code_to_name = _df[[string_column, code_column]].set_index(code_column).drop_duplicates().to_dict()[string_column]

    return {**_cat_map_code_to_name, **_cat_map_name_to_code}


def extend_time_features(_df: pd.DataFrame):
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


def add_history_columns(_df, n_intervals, value_column='rate', category_column='class_name'):
    # value_column is the column to get the history for
    # n_intervals are the number of history columns to add
    categories = _df[category_column].unique()
    for i in range(1, n_intervals+1):
        for c in categories:
            idx = _df.loc[_df[category_column] == c].index
            _df.loc[idx, f'-{i}'] = _df[_df[category_column] == c][value_column].shift(i)
    _df.dropna(inplace=True)
    return _df.reset_index(drop=True)


def add_future_columns(_df, n_intervals, value_column='rate', category_column='class_name'):
    # value_column is the column to get the history for
    # n_intervals are the number of history columns to add
    categories = _df[category_column].unique()
    for i in range(1, n_intervals+1):
        for c in categories:
            idx = _df.loc[_df[category_column] == c].index
            _df.loc[idx, f'+{i}'] = _df[_df[category_column] == c][value_column].shift(-i)
    _df.dropna(inplace=True)
    return _df.reset_index(drop=True)


def get_train_test_split(_df, hours_in_test=24, y_intervals=1):
    split_time = _df.time_stamp.max() - pd.Timedelta(f"{hours_in_test} hours")
    train = _df[_df.time_stamp < split_time]
    test = _df[_df.time_stamp >= split_time]

    X_train = train.drop(columns=['class_name', 'rate'] + [c for c in train.columns if c.startswith('+')]).reset_index(
        drop=True)
    X_test = test.drop(columns=['class_name', 'rate'] + [c for c in train.columns if c.startswith('+')]).reset_index(
        drop=True)

    future_columns = [f"+{c}" for c in range(1, y_intervals) if f"+{c}" in train.columns]
    y_train = np.squeeze(train[['rate'] + future_columns]).reset_index(drop=True)
    y_test = np.squeeze(test[['rate'] + future_columns]).reset_index(drop=True)

    return X_train, X_test, y_train, y_test, train, test


