import os
import datetime
import numpy as np
import pandas as pd
import pickle

from pygam import LinearGAM, s, f

from sklearn.metrics import r2_score

from .data_config import DataConfig

MODELS_DIR = 'app/trained_models'


class ModelConfig:
    def __init__(self, modelclass: LinearGAM,
                 data_config: DataConfig,
                 param_search: dict = None):
        if param_search is None:
            param_search: dict = {'lam': [.0001, .001, .1, 10, 50, 100, 400, 800, 1200, 1600, 2000, 2500]}
        self.modelclass: LinearGAM = modelclass
        self.data_config: DataConfig = data_config
        self.param_search: dict = param_search
        self.best_model = None
        self.best_score = 0
        self.filename = f"{self.data_config.monitor_name}_{self.data_config.interval}_{self.data_config.hours_in_training}_{self.data_config.hours_in_prediction}_{self.modelclass.__name__}"
        self.train_date = None
        self.set_best_model()

    def __str__(self):
        print_params = {'Model': self.modelclass.__name__,
                        'R2': self.best_score,
                        'Train Date': self.train_date}

        rv = ''
        for k, v in print_params.items():
            rv += f"{k:25}: {v}\n"
        rv += f"{self.data_config}"
        return rv

    @staticmethod
    def create(modelclass: LinearGAM,
               monitor_name: str,
               interval: int,
               hours_in_training: int,
               hours_in_prediction: int,
               string_predictor_columns: list = None,
               response_columns: list = None,
               source_data_from_date: str = None,
               param_search: dict = None):
        dc = DataConfig(monitor_name=monitor_name,
                        interval=interval,
                        hours_in_training=hours_in_training,
                        hours_in_prediction=hours_in_prediction,
                        string_predictor_columns=string_predictor_columns,
                        response_columns=response_columns,
                        source_data_from_date=source_data_from_date)
        mc = ModelConfig(modelclass=modelclass,
                         data_config=dc,
                         param_search=param_search)
        mc.save()
        return mc

    def get_best_model(self):
        return self.best_model

    def get_filename(self):
        return self.filename

    def predict(self, from_date=None):
        pred_df = self.string_predictions(from_date)
        pred_df = pred_df[['time_stamp', 'class_name', 'rate']]
        pred_df.rename(columns={'rate': 'count'}, inplace=True)
        return pred_df.to_dict(orient='list')

    def set_best_model(self):

        X, y = self.data_config.get_full_prediction_set()

        terms = None
        for i, c in enumerate(X.columns):
            if c.startswith('-') or c.startswith('+'):
                if terms == None:
                    terms = s(i)
                else:
                    terms += s(i)
            else:
                if terms == None:
                    terms = f(i)
                else:
                    terms += f(i)

        best_model = self.modelclass(terms=terms).gridsearch(X.to_numpy(), y.to_numpy(),
                                                             return_scores=False,
                                                             keep_best=True, objective='auto',
                                                             **self.param_search)

        self.best_score = r2_score(best_model.predict(X), y)
        self.train_date = datetime.datetime.now().date().isoformat()

        self.best_model = best_model

    def string_predictions(self, from_date=None):
        print("STRING PREDICTIONS")
        print("MODEL CONFIG:")
        print(self)

        d = self.data_config
        m = self.best_model

        n_train_intervals = d.hours_in_training * int(60 / d.interval)
        n_pred_intervals = d.hours_in_prediction * int(60 / d.interval)
        n_predictors = len([c for c in d.predictor_columns if not c.startswith('-')])

        X, time_zero = d.get_seed_observation(on_date=from_date)

        # String predictions
        for i in range(1, n_pred_intervals + 1):
            r = list(range(n_predictors)) + list(range(len(X.columns) - n_train_intervals, len(X.columns)))
            X[f"+{i}"] = np.clip(m.predict(X.iloc[:, r]), a_min=0, a_max=None)

        # Get initial DF with prediction columns
        r = list(range(n_predictors)) + list(range(len(X.columns) - n_pred_intervals, len(X.columns)))
        X = X.iloc[:, r]

        # insert the class name
        idx = int(np.where(X.columns == 'class_code')[0][0])
        X.insert(idx + 1, 'class_name', X['class_code'].apply(lambda s: d.get_category(s)))

        # rename future period columns to timestamp values
        time_stamps = [time_zero + pd.Timedelta(f'{d.interval * i} minutes') for i in range(1, n_pred_intervals + 1)]
        col_mapper = {old_c: time_stamps[int(old_c) - 1] for old_c in X.columns if old_c.startswith('+')}

        id_vars = [c for c in X.columns if not c.startswith('+')]

        X.rename(columns=col_mapper, inplace=True)

        X = pd.melt(X, id_vars=id_vars, var_name='time_stamp', value_name='rate')

        X = d.add_time_features(X)

        return X

    def save(self):
        """ Save model parameters without data.  Fresh data is retrieved when configuration is loaded."""

        save_params = {'model_config': self}

        file = os.path.join(MODELS_DIR, self.filename + '.pkl')

        # remove file if it already exists
        if os.path.exists(file):
            os.remove(file)

        with open(file, 'xb') as pkl_file:
            pickle.dump(self, pkl_file)

        return self.filename

    def is_saved(self):
        for file in os.listdir(MODELS_DIR):
            b, e = os.path.splitext(file)
            if b == self.filename or file == self.filename:
                return True
        return False

    @staticmethod
    def load(filename: str):
        """ Load model configuration.  Auto loads new observations from database. """
        filename = os.path.join(MODELS_DIR, filename)

        with open(filename + '.pkl', 'rb') as pkl_file:
            args = pickle.load(pkl_file)

        return args
