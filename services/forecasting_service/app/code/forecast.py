import pandas as pd
import numpy as np
from .utils import add_category_codes, extend_time_features, get_cat_map


def string_predictions(trained_model, _test_df, train_x_cols, train_y_cols, interval):

    cat_map = get_cat_map(_test_df, 'class_name', 'class_code')

    n_intervals = len([c for c in train_x_cols if c.startswith('-')])  # add 1 for the rate column
    n_predictors = 1 if type(train_y_cols) == str else len([c for c in train_y_cols])
    _test_df = _test_df.reset_index(drop=True)

    # get the first test observation that includes all cateogries
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
    time_stamps = [t + pd.Timedelta(f'{interval * (i + 1)} minutes') for i, _ in enumerate(pred_df.index)]
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

