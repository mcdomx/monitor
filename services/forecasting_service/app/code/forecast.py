from pygam import LinearGAM, s, f
from sklearn.metrics import r2_score
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

from .model_config import *
from .model_inventory import ModelInventory


# def execute_grid_search(m_config, model, param_search) -> dict:
#     results = {}
#
# _tr_x, _tr_y, _te_x, _te_y = m_config.get_train_test_split()
#
#     print("Evaluating Model")
#     print(f"Hours in Training: {m_config.hours_in_training}")
#     print(f"Hours in Prediction: {m_config.hours_in_prediction}")
#     print(f"Interval in Minutes: {m_config.interval}")
#     print(f"Start Training from UTC: {m_config.from_date_utc}")
#
#     # LinerGAM is not a a scikit model and will be handled separately.
#     # The only pramter we use here is the lam (aka - smoother)
#     if model.__class__.__name__ == "LinearGAM":
#         best_score = 0
#         for lam in param_search.get('lam'):
#             terms = None
#             for i, c in enumerate(_tr_x.columns):
#                 if c.startswith('-') or c.startswith('+'):
#                     if terms == None:
#                         terms = s(i, lam=lam)
#                     else:
#                         terms += s(i, lam=lam)
#                 else:
#                     if terms == None:
#                         terms = f(i)
#                     else:
#                         terms += f(i)
#             _m = LinearGAM(terms=terms)
#             y_pred = np.clip(_m.fit(_tr_x, _tr_y).predict(_te_x), a_min=0, a_max=None)
#             _score = r2_score(y_true=_te_y, y_pred=y_pred)
#             prev_best_score = 0
#             best_lam = 0
#             prev_score = _score
#             if _score > best_score:
#                 best_score = _score
#                 best_lam = lam
#                 best_model = _m
#
#             print(f"lam: {lam:5}  r2: {_score}")
#             if _score-prev_score <= .001 or _score < prev_best_score:
#                 break
#
#         best_params = f"\tlam: {best_lam}"
#
#     else:
#         tscv = TimeSeriesSplit(n_splits=8)
#         gsearch = GridSearchCV(estimator=model, cv=tscv, param_grid=param_search, scoring='r2', verbose=0, n_jobs=-1)
#         gsearch.fit(_tr_x, _tr_y)
#         best_model = gsearch.best_estimator_
#         y_pred = np.clip(best_model.predict(_te_x), a_min=0, a_max=None)
#         best_score = r2_score(y_true=_te_y, y_pred=y_pred)
#         best_params = f"\t{' | '.join([f'{p}: {str(getattr(best_model, p))}' for p in param_search])}"
#
#     print()
#     print(model.__class__.__name__)
#     print(f"Train Cols: {[c for c in _tr_x.columns if not (c.startswith('-'))]}")
#     print(f"\tBest Model's R2 Score: {round(best_score, 4)}")
#     print(f"\tBest Parameters: {best_params}")
#     print(f"\tScore By Class:")
#     for class_name in m_config.categories:
#         idxs = _te_x[_te_x.class_code == m_config.get_code(class_name)].index
#         r2 = r2_score(y_true=_te_y[idxs], y_pred=y_pred[idxs])
#         print(f"\t\t{class_name:10}: {round(r2, 4):>6}")
#         results.update({class_name: r2})
#
#     results.update({'best_model': best_model})
#     results.update({'best_overall_score': best_score})
#
#     return {model.__class__.__name__: results}
#
#
# def get_best_model(m_config):
#     models_to_evaluate = []
#
#     models_to_evaluate.append({'model': LinearGAM(),
#                                'param_search': {
#                                                #'lam': [500, 725, 750, 775, 800, 825, 850, 875, 1000],
#                                                 'lam': [.1, 10, 50, 100, 400, 800, 1200, 1600, 2000, 2500],
#                                                }
#                               })
#
# #     models_to_evaluate.append( {'model': RandomForestRegressor(n_jobs=-1, random_state=0),
# #                                 'param_search': {
# #                                                  'n_estimators': [10, 50, 100, 150],
# #                                                  'max_features': ['auto'], #, 'sqrt', 'log2'], -> the best scores are always auto
# #                                                  'max_depth' : [i for i in range(5,15)]
# #                                                 }
# #                                })
#
# #     models_to_evaluate.append( {'model': GradientBoostingRegressor(random_state=0),
# #                                 'param_search': {
# #                                                  'n_estimators': [20, 50, 100],
# #                                                  'learning_rate' : [.05, .1, .5, 1],
# #                                                  'loss' : ['ls', 'lad', 'huber', 'quantile']
# #                                                 }
# #                                })
#
#     evaluation_results = {}
#     for m in models_to_evaluate:
#         r = execute_grid_search(m_config, m.get('model'), m.get('param_search'))
#         evaluation_results.update(r)
#
#     results_df = pd.DataFrame(evaluation_results).T
#     return results_df[results_df.best_overall_score == results_df.best_overall_score.max()]['best_model'][0]


def string_predictions(m_config: ModelConfig, trained_model, from_date=None):
    print("STRING PREDICTIONS")
    print("MODEL CONFIG:")
    print(m_config)
    print("LINEAR GAM SUMMARY")
    print(trained_model.summary())

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

    X = m_config._add_time_features(X)

    return X


# def create_forecast(monitor_name, interval, hours_in_training, hours_in_prediction,
#                     source_data_from_date: str = None):
#     m_config = ModelConfig(monitor_name=monitor_name,
#                            interval=interval,
#                            hours_in_training=hours_in_training,
#                            hours_in_prediction=hours_in_prediction,
#                            source_data_from_date=source_data_from_date)
#
#     pred_df = string_predictions(m_config=m_config,
#                                  trained_model=get_best_model(m_config),
#                                  from_date=None)
#
#     # pred_df = pred_df[pred_df.class_name.isin(categories)][['time_stamp', 'class_name', 'rate']]
#     pred_df = pred_df[['time_stamp', 'class_name', 'rate']]
#
#     pred_df.rename(columns={'rate': 'count'}, inplace=True)
#
#     return pred_df.to_dict(orient='list')


def get_predictions(monitor_name: str,
                    interval: int = None,
                    hours_in_prediction: int = None,
                    hours_in_training: int = None):
    """ Uses the best performing model based on the parameters given """
    # config_args, model_args = ModelConfig.load(filename)
    #
    # m_config = ModelConfig(**config_args)
    #
    # X, y = m_config.get_full_prediction_set()

    m_config, trained_model = ModelInventory().get(monitor_name=monitor_name,
                                                   interval=interval,
                                                   hours_in_prediction=hours_in_prediction,
                                                   hours_in_training=hours_in_training)

    # trained_model = LinearGAM().set_params(**model_args).fit(X, y)

    pred_df = string_predictions(m_config=m_config,
                                 trained_model=trained_model,
                                 from_date=None)

    pred_df = pred_df[['time_stamp', 'class_name', 'rate']]

    pred_df.rename(columns={'rate': 'count'}, inplace=True)

    return pred_df.to_dict(orient='list')
