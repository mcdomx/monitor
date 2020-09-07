import threading
import logging
import json
from abc import ABCMeta, abstractmethod

from confluent_kafka import Consumer, TopicPartition, OFFSET_END

logger = logging.getLogger('service')


class ServiceAbstract(threading.Thread, metaclass=ABCMeta):

    def __init__(self, monitor_config, output_data_topic):
        threading.Thread.__init__(self)
        self.monitor_config = monitor_config
        self.output_data_topic = output_data_topic
        self.monitor_name = monitor_config.get('monitor_name')
        self.pulse = 1
        self.running = False

        # Kafka settings
        self.consumer = Consumer({
            'bootstrap.servers': '127.0.0.1:9092',
            'group.id': 'monitorgroup',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(topics=[self.monitor_config.get('monitor_name')], on_revoke=self.on_revoke)
        partitions = [TopicPartition(self.monitor_config.get('monitor_name'), p, OFFSET_END) for p in range(3)]
        self.consumer.assign(partitions)

    def update_monitor_config(self, monitor_config):
        self.monitor_config = monitor_config

    def on_revoke(self, consumer, partitions) -> (Consumer, list):
        if not self.running:
            return
        logger.info(f"ServiceAbstract subscriber on_revoke triggered.  Resetting consumer.")
        consumer = Consumer({
            'bootstrap.servers': '127.0.0.1:9092',
            'group.id': 'monitorgroup',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(topics=[self.monitor_config.get('monitor_name')], on_revoke=self.on_revoke)
        partitions = [TopicPartition(self.monitor_config.get('monitor_name'), p) for p in range(3)]
        self.consumer.assign(partitions)
        return consumer, partitions

    def start(self) -> dict:
        """
        Overriding Threading.start() so that we can test if thr service is
        already active and set the 'running' variable.
        :return: A dict with bool 'success' and string 'message' describing result.
        """
        if self.running:
            message = {'message': f"[{self.__class__.__name__}] Service is already running: {self.monitor_name}"}
            return message
        try:
            self.running = True
            threading.Thread.start(self)
            message = {'message': f"[{self.__class__.__name__}] Service started for: {self.monitor_name}"}
            return message
        except Exception as e:
            raise Exception(f"[{self.__class__.__name__}] Could not start '{self.monitor_name}': {e}")

    def stop(self):
        self.running = False

    def poll_kafka(self, timeout=0):
        msg = self.consumer.poll(timeout)

        # key = msg.key().decode('utf-8')
        # msg = msg.value().decode('utf-8')

        if msg is None:
            return None
        if msg.error():
            logger.info(f"[{self.__class__.__name__}] Consumer error: {msg.error()}")
            return None

        # the abstract class handles configuration changes
        self._handle_config_change(msg)

        return msg

    @abstractmethod
    def handle_message(self, msg) -> (str, object):
        """
        Any class inheriting ServiceAbstract should implement
        this method to handle message of a particular key.
        The AbstractService class will handle 'config_change' which does not
        need to be implemented.
        :param msg: kafka message object
        :return: tuple of (key, msg value)
        """
        ...

    def _handle_config_change(self, msg):
        """
        The abstract class will handle message with the key 'config_change'.
        Any other messages that the class should handle should be handled in
        the handle_message() method in the abstract class's implementation.
        :param msg: kafka message object
        :return: tuple of (key, msg value)
        """
        msg_key = msg.key().decode('utf-8')

        if msg_key == 'config_change':

            msg_value = json.JSONDecoder().decode(msg.value().decode('utf-8'))
            function_name = msg_value.get('function')

            logger.info(f"'{self.__class__.__name__}' handling: {msg_value}")

            # kwargs is a list of two-element dicts with 'field' and 'value' keys.
            # These are converted into a single dict to be used as a kwargs parameter
            # when calling the respective function named in the message.
            kwargs_list: list = msg_value.get('kwargs')
            kwargs = {p['field']: p['value'] for p in kwargs_list}

            try:
                f = getattr(self, function_name)
                if function_name is None or not callable(f):
                    # The published message can't be handled by this observer
                    logger.info(f"function not implemented or subject name not given: {function_name}")
                    return
                # execute function with or without kwargs
                if kwargs:
                    f(kwargs)
                else:
                    f()
                return

            except AttributeError as e:
                logger.error(e)

    # def handle_update(self, context: dict):
    #
    #     subject_name = context.get('subject')
    #     function_name = context.get('function')
    #     kwargs = context.get('kwargs')
    #
    #     try:
    #         f = getattr(self, function_name)
    #         if subject_name is None or function_name is None or not callable(f):
    #             # The published message can't be handled by this observer
    #             logger.info(f"function not implemented or subject name not given: {function_name} {subject_name}")
    #             return
    #         if kwargs:
    #             return f(kwargs)
    #         else:
    #             return f()
    #     except AttributeError as e:
    #         logger.error(e)
    #         return {'error': e.args}

    # def update(self, context: dict):
    #     """
    #     Any context dictionary received will be handled by the handle_update function.
    #
    #     :param context: {'subject': 'monitor_config',
    #                      'function': 'set_value',
    #                      'kwargs': {field: value}}
    #     :return: None
    #     """
    #     logger.info(f"{[{__name__}]} :UPDATED WITH: {context}")
    #     rv = self.handle_update(context)
    #     if rv:
    #         logger.info(f"{rv}")

    def set_value(self, kwargs):
        logger.info(f"Setting value: {kwargs}")
        for field, value in kwargs.items():
            self.monitor_config.update({field: value})
            # setattr(self, field, value)
        return
