

from .utils import *


def _get_master_df(monitor_name, interval, hours_to_predict, classes_to_predict, from_date):
    rs = get_rs(monitor_name=monitor_name, categories=classes_to_predict, from_date=from_date)
    _df = set_interval(pd.DataFrame(rs), interval=interval)
    _df = add_category_codes(_df, 'class_name', 'class_code')
    _df = extend_time_features(_df)
    _df = add_history_columns(_df, value_column='rate',
                              category_column='class_name',
                              n_intervals=hours_to_predict * int((60 / interval)))
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
    return results_df[results_df.best_overall_score == results_df.best_overall_score.max()]['best_model']


def string_predictions(trained_model, _test_df, train_x_cols, train_y_cols, interval):

    cat_map = get_cat_map(_test_df, 'class_name', 'class_code')

    n_intervals = len([c for c in train_x_cols if c.startswith('-')])  # add 1 for the rate column
    n_predictors = 1 if type(train_y_cols) == str else len([c for c in train_y_cols])
    _test_df = _test_df.reset_index(drop=True)

    # get the first test observation that includes all cateogories
    found = False
    i = 0
    t = None
    while not found:
        t = _test_df.iloc[i].time_stamp
        if set(_test_df[_test_df.time_stamp == t].class_name.values) == set(_test_df.class_name.unique()):
            found = True

    # create the starting point from which to string future predictions
    X = _test_df[_test_df.time_stamp == t][train_x_cols].copy().reset_index(drop=True)

    # String predictions
    for i in range(n_intervals + 1):
        r = list(range(n_predictors)) + list(range(len(X.columns) - n_intervals, len(X.columns)))
        X[f"+{i}"] = np.clip(trained_model.predict(X.iloc[:, r]), a_min=0, a_max=None)

    # Reformat results into dataframe of similar stucture to the original train and test dataframes
    pred_df = X.iloc[:, r].T.iloc[1:, :]
    time_stamps = [t + pd.Timedelta(f'{interval * i } minutes') for i, _ in enumerate(pred_df.index)]
    pred_df.index = time_stamps

    # rename the columns
    pred_df.columns = [cat_map.get(c) for c in pred_df.columns]

    # melt the columns
    pred_df = pred_df.melt(ignore_index=False, var_name='class_name', value_name='rate').reset_index().rename(
        columns={'index': 'time_stamp'})

    # extend a colum for the codes the codes
    pred_df = add_category_codes(pred_df, 'class_name', 'class_code')

    # extend columns for time characteristics
    pred_df = extend_time_features(pred_df)

    return pred_df


def create_forecast(monitor_name, prediction_interval=60, hours_to_predict=24, classes_to_predict=None, from_date=None):
    _df = _get_master_df(monitor_name,
                         interval=prediction_interval,
                         hours_to_predict=hours_to_predict,
                         classes_to_predict=classes_to_predict,
                         from_date=from_date)

    X_train, X_test, y_train, y_test, train_df, test_df = get_train_test_split(_df, hours_in_test=hours_to_predict, y_intervals=1)

    train_x_cols = ['class_code'] + [c for c in train_df.columns[::-1] if c.startswith('-')]
    train_y_cols = 'rate'

    best_model = _get_best_model(train_df, test_df, train_x_cols, train_y_cols)

    pred_df = string_predictions(best_model, test_df, train_x_cols, train_y_cols, prediction_interval)

    return pred_df

