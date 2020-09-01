import threading
import logging
from traffic_monitor.services.observer import Subject, Observer
from abc import ABCMeta, abstractmethod

logger = logging.getLogger('service')


class ServiceAbstract(threading.Thread, Subject, Observer, metaclass=ABCMeta):

    def __init__(self, monitor_config):
        threading.Thread.__init__(self)
        Subject.__init__(self)
        Observer.__init__(self)
        self.monitor_config = monitor_config
        self.monitor_name = monitor_config.get('monitor_name')

    def update_monitor_config(self, monitor_config):
        self.monitor_config = monitor_config

    @abstractmethod
    def stop(self):
        ...

    def handle_update(self, context: dict):

        subject_name = context.get('subject')
        function_name = context.get('function')
        kwargs = context.get('kwargs')

        try:
            f = getattr(self, function_name)
            if subject_name is None or function_name is None or not callable(f):
                # The published message can't be handled by this observer
                logger.info(f"function not implemented or subject name not given: {function_name} {subject_name}")
                return
            if kwargs:
                return f(kwargs)
            else:
                return f()
        except AttributeError as e:
            logger.error(e)
            return {'error': e.args}

    def update(self, context: dict):
        """
        Any context dictionary received will be handled by the handle_update function.

        :param context: {'subject': 'monitor_config',
                         'function': 'set_value',
                         'kwargs': {field: value}}
        :return: None
        """
        logger.info(f"{[{__name__}]} :UPDATED WITH: {context}")
        rv = self.handle_update(context)
        if rv:
            logger.info(f"{rv}")

    def set_value(self, kwargs):
        for field, value in kwargs.items():
            setattr(self, field, value)
        return


