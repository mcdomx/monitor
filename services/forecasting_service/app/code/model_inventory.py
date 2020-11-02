import os
import pandas as pd

from pygam import LinearGAM

from .model_config import ModelConfig, MODELS_DIR


class ModelInventory:
    """ Loads a reference to all models that are stored in MODEL_DIR"""
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
            cls.singleton.load_models()
        return cls.singleton

    class _Singleton:

        def __init__(self):
            self.all_df: pd.DataFrame = pd.DataFrame(
                columns=['monitor_name', 'file_name', 'interval',
                         'hours_in_prediction', 'hours_in_training',
                         'score', 'train_date', 'model_type', 'model_config'])

        def add(self, mc: ModelConfig):
            # remove item if it already exists
            try:
                ridx = self.all_df[self.all_df.file_name == mc.filename].index.values
                self.all_df = self.all_df.drop(ridx)
            except:
                pass

            s = pd.Series({'monitor_name': mc.data_config.monitor_name,
                           'file_name': mc.filename,
                           'interval': mc.data_config.interval,
                           'hours_in_prediction': mc.data_config.hours_in_prediction,
                           'hours_in_training': mc.data_config.hours_in_training,
                           'score': mc.best_score,
                           'train_date': mc.train_date,
                           'model_type': mc.modelclass.__name__,
                           'model_config': mc})
            self.all_df = self.all_df.append(s, ignore_index=True)

        def create_model(self,
                         monitor_name: str,
                         interval: int,
                         hours_in_training: int,
                         hours_in_prediction: int,
                         modelclass: LinearGAM = LinearGAM,
                         string_predictor_columns: list = None,
                         response_columns: list = None,
                         source_data_from_date: str = None,
                         param_search: dict = None):
            mc = ModelConfig.create(modelclass=modelclass,
                                    monitor_name=monitor_name,
                                    interval=interval,
                                    hours_in_prediction=hours_in_prediction,
                                    hours_in_training=hours_in_training,
                                    string_predictor_columns=string_predictor_columns,
                                    response_columns=response_columns,
                                    source_data_from_date=source_data_from_date,
                                    param_search=param_search)
            self.add(mc)
            return mc.filename

        def get(self, monitor_name: str, interval: int, hours_in_prediction: int, hours_in_training: int):
            """ Returns best performing model based on filter criteria supplied """

            _df = self.all_df[self.all_df.monitor_name == monitor_name]

            if interval is not None:
                _df = _df[_df.interval == interval]
            if hours_in_prediction is not None:
                _df = _df[_df.hours_in_prediction == hours_in_prediction]
            if hours_in_training is not None:
                _df = _df[_df.hours_in_training == hours_in_training]

            # get the best scoring model
            _df = _df[_df.score == _df.score.max()]

            if len(_df) == 0:
                return None

            m = _df.model_config.iloc[0]

            return m

        @staticmethod
        def get_by_filename(filename):
            return ModelConfig.load(filename)

        def retrain_by_filename(self, filename):
            mc = ModelConfig.load(filename)
            mc.data_config.update_data()
            mc.set_best_model()
            self.add(mc)
            return mc.filename

        def retrain_all(self):
            for filename in self.all_df.file_name.values:
                self.retrain_by_filename(filename)

        def get_inventory_listing(self, monitor_name: str) -> dict:
            _df = self.all_df[self.all_df.monitor_name == monitor_name]
            _df = _df[
                ['monitor_name', 'model_type', 'file_name', 'interval', 'hours_in_prediction', 'hours_in_training',
                 'score', 'train_date']]
            _df.set_index(['file_name'], drop=True, inplace=True)
            return _df.to_dict(orient='index')

        def get_inventory_item(self, filename: str) -> dict:
            _df = self.all_df[self.all_df.file_name == filename]
            _df = _df[
                ['monitor_name', 'model_type', 'file_name', 'interval', 'hours_in_prediction', 'hours_in_training',
                 'score', 'train_date']]
            _df.set_index(['file_name'], drop=True, inplace=True)
            return _df.to_dict(orient='index')

        def load_models(self):
            """ Load all saved model files into dataframe """
            # re-initialize the class to erase the df of models stored - avoids double-loading if
            # this method is called from outside
            self.__init__()

            # get list of all saved model files
            for file in os.listdir(MODELS_DIR):
                f_name, f_ext = os.path.splitext(file)
                if f_ext == '.pkl':
                    mc = ModelConfig.load(f_name)
                    # if type(mc) == dict:
                    #     os.remove(os.path.join(MODELS_DIR, file))
                    # else:
                    self.add(mc)


def get_predictions(monitor_name: str,
                    interval: int = None,
                    hours_in_prediction: int = None,
                    hours_in_training: int = None):
    """ Uses the best performing model based on the parameters given """
    """ time_stamp is tz-aware in UTC"""

    m_config: ModelConfig = ModelInventory().get(monitor_name=monitor_name,
                                                 interval=interval,
                                                 hours_in_prediction=hours_in_prediction,
                                                 hours_in_training=hours_in_training)

    if m_config is None:
        mc_filename = ModelInventory().create_model(monitor_name=monitor_name,
                                                    interval=interval,
                                                    hours_in_prediction=hours_in_prediction,
                                                    hours_in_training=hours_in_training)
        m_config = ModelInventory().get_by_filename(mc_filename)

    pred_df = m_config.predict()

    return pred_df


def setup_default_models(monitor_name):
    """ Trains and saves pre-determined default models that are ready for making predictions.
    Ensures that there is at lesat one model to use for forecasting. """

    # only load default models if the Inventory is empty
    if len(ModelInventory().get_inventory_listing(monitor_name)) > 0:
        return

    d = {'monitor_name': monitor_name,
         'interval': 60,
         'hours_in_training': 24 * 1,
         'hours_in_prediction': 48,
         'string_predictor_columns': ['class_code', 'weekday', 'hour'],
         'source_data_from_date': '2020-10-01'}
    ModelInventory().create_model(**d)

    # d = {'monitor_name': monitor_name,
    #      'interval': 60,
    #      'hours_in_training': 24 * 1,
    #      'hours_in_prediction': 48,
    #      'string_predictor_columns': ['class_code', 'weekday', 'hour'],
    #      'source_data_from_date': '2020-10-01'}
    # ModelInventory().create_model(**d)
    #
    # d = {'monitor_name': monitor_name,
    #      'interval': 60,
    #      'hours_in_training': 24 * 2,
    #      'hours_in_prediction': 48,
    #      'string_predictor_columns': ['class_code', 'weekday', 'hour'],
    #      'source_data_from_date': '2020-10-01'}
    # ModelInventory().create_model(**d)
    #
    # d = {'monitor_name': monitor_name,
    #      'interval': 60,
    #      'hours_in_training': 24 * 3,
    #      'hours_in_prediction': 48,
    #      'string_predictor_columns': ['class_code', 'weekday', 'hour'],
    #      'source_data_from_date': '2020-10-01'}
    # ModelInventory().create_model(**d)
    #
    # d = {'monitor_name': monitor_name,
    #      'interval': 60,
    #      'hours_in_training': 24 * 4,
    #      'hours_in_prediction': 48,
    #      'string_predictor_columns': ['class_code', 'weekday', 'hour'],
    #      'source_data_from_date': '2020-10-01'}
    # ModelInventory().create_model(**d)
    #
    # d = {'monitor_name': monitor_name,
    #      'interval': 60,
    #      'hours_in_training': 24 * 5,
    #      'hours_in_prediction': 48,
    #      'string_predictor_columns': ['class_code', 'weekday', 'hour'],
    #      'source_data_from_date': '2020-10-01'}
    # ModelInventory().create_model(**d)
    #
    # d = {'monitor_name': monitor_name,
    #      'interval': 60,
    #      'hours_in_training': 24 * 6,
    #      'hours_in_prediction': 48,
    #      'string_predictor_columns': ['class_code', 'weekday', 'hour'],
    #      'source_data_from_date': '2020-10-01'}
    # ModelInventory().create_model(**d)
    #
    # d = {'monitor_name': monitor_name,
    #      'interval': 60,
    #      'hours_in_training': 24 * 7,
    #      'hours_in_prediction': 48,
    #      'string_predictor_columns': ['class_code', 'weekday', 'hour'],
    #      'source_data_from_date': '2020-10-01'}
    # ModelInventory().create_model(**d)


setup_default_models('MyMonitor')
