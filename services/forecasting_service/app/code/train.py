import numpy as np
from pygam import LinearGAM, s, f
from sklearn.metrics import r2_score
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
import pandas as pd

from .model_config import ModelConfig
from .model_inventory import ModelInventory


def execute_grid_search(m_config, model, param_search) -> dict:
    results = {}

    _tr_x, _tr_y, _te_x, _te_y = m_config.get_train_test_split()

    print("Evaluating Model")
    print(f"Hours in Training: {m_config.hours_in_training}")
    print(f"Hours in Prediction: {m_config.hours_in_prediction}")
    print(f"Interval in Minutes: {m_config.interval}")
    print(f"Start Training from UTC: {m_config.from_date_utc}")

    # LinerGAM is not a a scikit model and will be handled separately.
    # The only pramter we use here is the lam (aka - smoother)
    if model.__class__.__name__ == "LinearGAM":
        best_score = 0
        prev_score = 0
        prev_best_score = 0
        best_lam = 0
        for lam in param_search.get('lam'):
            terms = None
            for i, c in enumerate(_tr_x.columns):
                if c.startswith('-') or c.startswith('+'):
                    if terms == None:
                        terms = s(i, lam=lam)
                    else:
                        terms += s(i, lam=lam)
                else:
                    if terms == None:
                        terms = f(i)
                    else:
                        terms += f(i)
            _m = LinearGAM(terms=terms)
            y_pred = np.clip(_m.fit(_tr_x, _tr_y).predict(_te_x), a_min=0, a_max=None)
            _score = r2_score(y_true=_te_y, y_pred=y_pred)

            if _score > best_score:
                prev_best_score = best_score
                best_score = _score
                best_lam = lam
                best_model = _m

            print(f"lam: {lam:5}  r2: {_score}")
            if _score - prev_score <= .001 or _score < prev_best_score:
                break

            prev_score = _score

        best_params = f"\tlam: {best_lam}"

    else:
        tscv = TimeSeriesSplit(n_splits=8)
        gsearch = GridSearchCV(estimator=model, cv=tscv, param_grid=param_search, scoring='r2', verbose=0, n_jobs=-1)
        gsearch.fit(_tr_x, _tr_y)
        best_model = gsearch.best_estimator_
        y_pred = np.clip(best_model.predict(_te_x), a_min=0, a_max=None)
        best_score = r2_score(y_true=_te_y, y_pred=y_pred)
        best_params = f"\t{' | '.join([f'{p}: {str(getattr(best_model, p))}' for p in param_search])}"

    print()
    print(model.__class__.__name__)
    print(f"Train Cols: {[c for c in _tr_x.columns if not (c.startswith('-'))]}")
    print(f"\tBest Model's R2 Score: {round(best_score, 4)}")
    print(f"\tBest Parameters: {best_params}")
    print(f"\tScore By Class:")
    for class_name in m_config.categories:
        idxs = _te_x[_te_x.class_code == m_config.get_code(class_name)].index
        r2 = r2_score(y_true=_te_y[idxs], y_pred=y_pred[idxs])
        print(f"\t\t{class_name:10}: {round(r2, 4):>6}")
        results.update({class_name: r2})

    results.update({'best_model': best_model})
    results.update({'best_overall_score': best_score})

    return {model.__class__.__name__: results}


def get_best_model(m_config):
    models_to_evaluate = []

    models_to_evaluate.append({'model': LinearGAM(),
                               'param_search': {
                                   'lam': [.1, 10, 50, 100, 400, 800, 1200, 1600, 2000, 2500],
                               }
                               })

    #     models_to_evaluate.append( {'model': RandomForestRegressor(n_jobs=-1, random_state=0),
    #                                 'param_search': {
    #                                                  'n_estimators': [10, 50, 100, 150],
    #                                                  'max_features': ['auto'], #, 'sqrt', 'log2'], -> the best scores are always auto
    #                                                  'max_depth' : [i for i in range(5,15)]
    #                                                 }
    #                                })

    #     models_to_evaluate.append( {'model': GradientBoostingRegressor(random_state=0),
    #                                 'param_search': {
    #                                                  'n_estimators': [20, 50, 100],
    #                                                  'learning_rate' : [.05, .1, .5, 1],
    #                                                  'loss' : ['ls', 'lad', 'huber', 'quantile']
    #                                                 }
    #                                })

    evaluation_results = {}
    for m in models_to_evaluate:
        r = execute_grid_search(m_config, m.get('model'), m.get('param_search'))
        evaluation_results.update(r)

    results_df = pd.DataFrame(evaluation_results).T
    return results_df[results_df.best_overall_score == results_df.best_overall_score.max()]['best_model'][0]


def train_and_save(monitor_name, interval,
                   hours_in_training, hours_in_prediction,
                   string_predictor_columns,
                   source_data_from_date: str = None):
    """ Train model """

    m_config = ModelConfig(monitor_name=monitor_name,
                           interval=interval,
                           hours_in_training=hours_in_training,
                           hours_in_prediction=hours_in_prediction,
                           string_predictor_columns=string_predictor_columns,
                           source_data_from_date=source_data_from_date)

    trained_model: LinearGAM = get_best_model(m_config)

    filename = m_config.save(trained_model)

    ModelInventory().add(filename=filename, model_config=m_config, trained_model=trained_model)

    return filename


def retrain_by_filename(filename: str):
    m_config = ModelConfig.get_config_by_filename(filename)
    if m_config is None:
        return
    trained_model: LinearGAM = get_best_model(m_config)
    filename = m_config.save(trained_model)
    # update the inventory with the newly trained model
    return ModelInventory().add(filename=filename, model_config=m_config, trained_model=trained_model)


def setup_default_models(monitor_name):
    """ Trains and saves pre-determined default models that are ready for making predictions.
    Ensures that there is at lesat one model to use for forecasting. """

    default_models = []
    filenames = []
    model = {'monitor_name': monitor_name,
             'interval': 60,
             'hours_in_training': 24,
             'hours_in_prediction': 24,
             'string_predictor_columns': ['class_code', 'weekday', 'hour'],
             'source_data_from_date': '2020-10-01'}
    default_models.append(model)

    model = {'monitor_name': monitor_name,
             'interval': 60,
             'hours_in_training': 48,
             'hours_in_prediction': 24,
             'string_predictor_columns': ['class_code', 'weekday', 'hour'],
             'source_data_from_date': '2020-10-01'}
    default_models.append(model)

    for m in default_models:
        c = ModelConfig(**m)
        if not c.is_saved():
            filenames.append(train_and_save(**m))


def retrain_all(monitor_name):
    models = ModelInventory().get_inventory_listing(monitor_name=monitor_name)
    for fname in models:
        retrain_by_filename(fname)


# immediately ensure that at least one 'fresh' model is available
setup_default_models('MyMonitor')
