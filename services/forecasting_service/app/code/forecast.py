

from .utils import *


def _get_master_df(monitor_name, interval, predictor_hours, classes_to_predict, from_date):
    print("FROM _get_master_df")
    print(classes_to_predict)

    rs = get_rs(monitor_name=monitor_name, categories=classes_to_predict, from_date=from_date)
    _df = set_interval(pd.DataFrame(rs), interval=interval)
    print(_df.class_name.unique())
    _df = add_category_codes(_df, 'class_name', 'class_code')
    _df = extend_time_features(_df)
    _df = add_history_columns(_df,
                              value_column='rate',
                              category_column='class_name',
                              n_intervals=predictor_hours * int((60 / interval)))
    return _df


def _get_best_model(train_df, test_df, train_x_cols, train_y_cols):
    models_to_evaluate = []

    models_to_evaluate.append({'model': LinearGAM(),
                               'param_search': {
                                   # 'lam': [500, 725, 750, 775, 800, 825, 850, 875, 1000],
                                   'lam': [.1, 10, 50, 100, 400, 800, 1200, 1600, 2000],
                               }
                               })

    # models_to_evaluate.append({'model': RandomForestRegressor(n_jobs=-1, random_state=0),
    #                            'param_search': {
    #                                'n_estimators': [10, 50, 100, 150],
    #                                'max_features': ['auto'],  # , 'sqrt', 'log2'], -> the best scores are always auto
    #                                'max_depth': [i for i in range(5, 15)]
    #                            }
    #                            })

    evaluation_results = {}
    for m in models_to_evaluate:
        r = execute_grid_search(train_df, test_df, m.get('model'), m.get('param_search'), train_x_cols, train_y_cols)
        evaluation_results.update(r)

    results_df = pd.DataFrame(evaluation_results).T
    return results_df[results_df.best_overall_score == results_df.best_overall_score.max()]['best_model'][0]


def _get_seed_observation(monitor_name: str,
                          interval: int,
                          predictor_hours: int,
                          categories: list = None,
                          from_date: str = None):
    # get the most recent observation or the first observation on date
    # provided as from_date (is isoformat YYYY-MM_DDTHH:MM)
    # from_date is expected to be in the monitor's timezone
    time_zone = Monitor.objects.get(pk=monitor_name).feed.time_zone
    if from_date is None:
        from_date = LogEntry.objects.filter(monitor=monitor_name).latest('time_stamp').time_stamp.astimezone(
            pytz.timezone(time_zone))  # - pd.Timedelta(f'{predictor_hours} Hours')).isoformat()
    else:
        from_date = datetime.datetime.fromisoformat(
            from_date)  # .replace(tzinfo=pytz.timezone(time_zone)).astimezone(pytz.UTC)

    from_date = (from_date - pd.Timedelta(f'{predictor_hours + 1} Hours')).isoformat()

    _df = pd.DataFrame(get_rs(monitor_name='MyMonitor', categories=categories, from_date=from_date))
    _df = set_interval(_df, interval=interval)
    _df = add_category_codes(_df, 'class_name', 'class_code')
    _df = extend_time_features(_df)
    _df = add_history_columns(_df, value_column='rate', category_column='class_name',
                              n_intervals=predictor_hours * int((60 / interval)))
    _df = _df[_df.time_stamp == _df.time_stamp.min()]
    x_cols = ['class_code', 'time_stamp'] + [c for c in _df.columns if c.startswith('-')][::-1]

    if len(_df) == 0:
        raise Exception(f"Unable to get forecasting seed: monitor:{monitor_name}, interval:{interval}, 'pred_hours':{predictor_hours}, from_date:{from_date}, categories:{categories}")

    return _df[x_cols].reset_index(drop=True)


def string_predictions(monitor_name, trained_model, train_x_cols, train_y_cols, interval, predictor_hours, categories,
                       from_date=None):
    n_intervals = len([c for c in train_x_cols if c.startswith('-')])  # add 1 for the rate column
    n_predictors = 1 if type(train_y_cols) == str else len([c for c in train_y_cols])

    X = _get_seed_observation(monitor_name=monitor_name, interval=interval, predictor_hours=predictor_hours,
                              categories=categories, from_date=from_date)

    if len(X) == 0:
        raise Exception(f"Unable to get forecasting seed: monitor:{monitor_name}, interval:{interval}, 'pred_hours':{predictor_hours}, from_date:{from_date}, categories:{categories}")

    start_time = X.time_stamp[0]
    X.drop(columns=['time_stamp'], inplace=True)
    X.set_index(X.class_code.values, inplace=True)

    # String predictions
    for i in range(n_intervals + 1):
        r = list(range(n_predictors)) + list(range(len(X.columns) - n_intervals, len(X.columns)))
        X[f"+{i}"] = np.clip(trained_model.predict(X.iloc[:, r]), a_min=0, a_max=None)

    # Reformat results into dataframe of similar structure to the original train and test dataframes
    pred_df = X.iloc[:, r].T.iloc[1:, :]

    time_stamps = [start_time + pd.Timedelta(f'{interval * i} minutes') for i, _ in enumerate(pred_df.index)]
    pred_df.index = time_stamps

    # rename the columns
    pred_df.columns = categories.sort()

    # melt the columns
    pred_df = pred_df.melt(ignore_index=False, var_name='class_name', value_name='rate').reset_index().rename(
        columns={'index': 'time_stamp'})

    # extend a colum for the codes the codes
    pred_df = add_category_codes(pred_df, 'class_name', 'class_code')

    # extend columns for time characteristics
    pred_df = extend_time_features(pred_df)

    return pred_df


def create_forecast(monitor_name, interval, predictor_hours, classes_to_predict=None, from_date=None):

    print(classes_to_predict)

    _df = _get_master_df(monitor_name=monitor_name,
                         interval=interval,
                         predictor_hours=predictor_hours,
                         classes_to_predict=classes_to_predict,
                         from_date=from_date)

    if len(_df) == 0:
        raise Exception(f"No records to make prediction on. monitor_name:{monitor_name}, interval:{interval}, predictor_hours:{predictor_hours}, from_date:{from_date}, classes_to_predict:{classes_to_predict}")

    cat_map = get_cat_map(_df, 'class_name', 'class_code')
    categories = [c for c in cat_map.keys() if type(c) == str]
    print(_df.class_name.unique())

    X_train, X_test, y_train, y_test, train_df, test_df = get_train_test_split(_df, hours_in_test=predictor_hours,
                                                                               y_intervals=1)

    train_x_cols = ['class_code'] + [c for c in train_df.columns[::-1] if c.startswith('-')]
    train_y_cols = 'rate'

    best_model = _get_best_model(train_df, test_df, train_x_cols, train_y_cols)

    pred_df = string_predictions(monitor_name=monitor_name,
                                 trained_model=best_model,
                                 train_x_cols=train_x_cols,
                                 train_y_cols=train_y_cols,
                                 interval=interval,
                                 predictor_hours=predictor_hours,
                                 categories=categories,
                                 from_date=from_date)

    return pred_df.to_dict(orient='list')
