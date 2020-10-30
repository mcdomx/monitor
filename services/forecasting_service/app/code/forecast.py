
from .model_config import *
from .model_inventory import ModelInventory


def string_predictions(m_config: ModelConfig, trained_model, from_date=None):
    print("STRING PREDICTIONS")
    print("MODEL CONFIG:")
    print(m_config)
    # trained_model.summary()

    n_train_intervals = m_config.hours_in_training * int(60 / m_config.interval)
    n_pred_intervals = m_config.hours_in_prediction * int(60 / m_config.interval)
    n_predictors = len([c for c in m_config.predictor_columns if not c.startswith('-')])

    X, time_zero = m_config.get_seed_observation(on_date=from_date)

    # String predictions
    for i in range(1, n_pred_intervals + 1):
        r = list(range(n_predictors)) + list(range(len(X.columns) - n_train_intervals, len(X.columns)))
        X[f"+{i}"] = np.clip(trained_model.predict(X.iloc[:, r]), a_min=0, a_max=None)

    # Get initial DF with prediction columns
    r = list(range(n_predictors)) + list(range(len(X.columns) - n_train_intervals, len(X.columns)))
    X = X.iloc[:, r]

    # insert the class name
    idx = int(np.where(X.columns == 'class_code')[0][0])
    X.insert(idx + 1, 'class_name', X['class_code'].apply(lambda s: m_config.get_category(s)))

    # rename future period columns to timestamp values
    time_stamps = [time_zero + pd.Timedelta(f'{m_config.interval * i} minutes') for i in range(1, n_pred_intervals + 1)]
    col_mapper = {old_c: time_stamps[int(old_c) - 1] for old_c in X.columns if old_c.startswith('+')}

    id_vars = [c for c in X.columns if not c.startswith('+')]

    X.rename(columns=col_mapper, inplace=True)

    X = pd.melt(X, id_vars=id_vars, var_name='time_stamp', value_name='rate')

    X = m_config.add_time_features(X)

    return X


def get_predictions(monitor_name: str,
                    interval: int = None,
                    hours_in_prediction: int = None,
                    hours_in_training: int = None):
    """ Uses the best performing model based on the parameters given """
    """ time_stamp is tz-aware in UTC"""

    m_config, trained_model = ModelInventory().get(monitor_name=monitor_name,
                                                   interval=interval,
                                                   hours_in_prediction=hours_in_prediction,
                                                   hours_in_training=hours_in_training)

    if m_config is None or trained_model is None:
        return None

    pred_df = string_predictions(m_config=m_config,
                                 trained_model=trained_model,
                                 from_date=None)

    pred_df = pred_df[['time_stamp', 'class_name', 'rate']]

    pred_df.rename(columns={'rate': 'count'}, inplace=True)

    return pred_df.to_dict(orient='list')
