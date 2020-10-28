import os
import pytz
import pandas as pd

from pygam import LinearGAM

from .model_config import ModelConfig, MODELS_DIR


class ActiveModel:
    """ Bonds the model config with a trained model from the config"""

    def __init__(self, filename: str, model_config: ModelConfig, trained_model: LinearGAM):
        self.filename: str = filename
        self.model_config: ModelConfig = model_config
        self.trained_model: LinearGAM = trained_model
        self.score: float = model_config.get_score(trained_model)

    def __repr__(self):
        return f"filename: {self.filename}\nscore: {self.score}\ninterval: {self.model_config.interval}\nhours in training: {self.model_config.hours_in_training}\nhours in prediction: {self.model_config.hours_in_prediction}"

    def get_series(self):
        return pd.Series({'monitor_name': self.model_config.monitor_name,
                          'file_name': self.filename,
                          'interval': self.model_config.interval,
                          'hours_in_prediction': self.model_config.hours_in_prediction,
                          'hours_in_training': self.model_config.hours_in_training,
                          'source_data_from_date': self.model_config.from_date_utc.tz_convert(
                              pytz.timezone(self.model_config.time_zone)).replace(
                              tzinfo=None).isoformat(),
                          'score': self.score,
                          'active_model': self})

    # @classmethod
    # def from_file(cls, filename):
    #     return ModelConfig.load(filename)
    #     # return ActiveModel(filename, ModelConfig(**config_args), trained_model)


class ModelInventory:
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
            cls.singleton.load_models()
        return cls.singleton

    class _Singleton:

        def __init__(self):
            self.all_df: pd.DataFrame = pd.DataFrame(
                columns=['monitor_name', 'file_name', 'interval', 'hours_in_prediction', 'hours_in_training',
                         'source_data_from_date', 'score', 'active_model'])

        def add(self, filename: str, model_config: ModelConfig, trained_model: LinearGAM):
            # remove item if it already exists
            try:
                ridx = self.all_df[self.all_df.file_name == filename].index.values[0]
                self.all_df = self.all_df.drop(ridx)
            except:
                pass

            a = ActiveModel(filename=filename, model_config=model_config, trained_model=trained_model)
            self.all_df = self.all_df.append(a.get_series(), ignore_index=True)

            return filename

        def get(self, monitor_name: str, interval: int, hours_in_prediction: int, hours_in_training: int,
                source_data_from_date: str = None):
            """ Returns best performing model based on filter criteria supplied """
            _df = self.all_df[self.all_df.monitor_name == monitor_name]
            if interval is not None:
                _df = _df[_df.interval == interval]
            if hours_in_prediction is not None:
                _df = _df[_df.hours_in_prediction == hours_in_prediction]
            if hours_in_training is not None:
                _df = _df[_df.hours_in_training == hours_in_training]
            if source_data_from_date is not None:
                _df = _df[_df.source_data_from_date == source_data_from_date]

            # get the best scoring model
            _df = _df[_df.score == _df.score.max()]

            if len(_df) == 0:
                return None, None

            active_model = _df.active_model.iloc[0]

            return active_model.model_config, active_model.trained_model

        def get_inventory_listing(self, monitor_name: str) -> dict:
            _df = self.all_df[self.all_df.monitor_name == monitor_name]
            _df = _df[['monitor_name', 'file_name', 'interval', 'hours_in_prediction', 'hours_in_training', 'source_data_from_date', 'score']]
            _df.set_index(['file_name'], drop=True, inplace=True)
            return _df.to_dict(orient='index')

        def get_inventory_item(self, filename: str) -> dict:
            _df = self.all_df[self.all_df.file_name == filename]
            _df = _df[['monitor_name', 'file_name', 'interval', 'hours_in_prediction', 'hours_in_training', 'source_data_from_date', 'score']]
            _df.set_index(['file_name'], drop=True, inplace=True)
            return _df.to_dict(orient='index')

        def load_models(self):
            """ Load all saved model files into ActiveModels """

            # re-initialize the class to erase the df of models stored - avoids double-loading if
            # this method is called from outside
            self.__init__()

            # get list of all saved model files
            for f in os.listdir(MODELS_DIR):
                f_name, f_ext = os.path.splitext(f)
                if f_ext == '.pkl':
                    config_args, model_args, trained_model = ModelConfig.load(f_name)
                    self.add(filename=f_name, model_config=ModelConfig(**config_args), trained_model=trained_model)
