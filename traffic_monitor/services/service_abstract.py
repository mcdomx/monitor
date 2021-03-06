import threading
import logging
import json
import os
from abc import ABCMeta, abstractmethod

from confluent_kafka import Consumer, TopicPartition, OFFSET_END

logger = logging.getLogger('service')

KAFKA_HOST = os.getenv('KAFKA_HOST', '0.0.0.0')
KAFKA_PORT = os.getenv('KAFKA_PORT', 9092)
KAFKA_GROUPID = os.getenv('KAFKA_GROUPID', 'monitorgroup')

class ServiceAbstract(threading.Thread, metaclass=ABCMeta):
    """
    ServiceAbstract is an abstract class that should be implemented for each service of a monitor.
    This abstract class ensures that the service operates as a thread and will hold a monitor_config attribute
    which is maintained via Kafka messages to this abstract class.  Changes to the Monitor's persistent
    data store using the MonitorFactory() will send a message to the 'config_change' channel which this
    class will listen for and respectively update the monitor_config attribute.  This process ensures that each
    service keeps a current status of the monitor's settings and that each implementing class does not need
    to implement specific actions to keep the settings current.

    Each implemented service is expected to run as a thread.  The thread will be interrupted for configuration changes
    so that updates are immediate.

    """

    def __init__(self, monitor_config, output_data_topic):
        """

        :param monitor_config: The monitor's configuration dictionary which is retrieved via MonitorFactory().get_monitor_configuration(<monitor_name>).
        :param output_data_topic: If the implementation of the abstract class produces data, this is the topic name that will be used.
        """
        global KAFKA_HOST, KAFKA_PORT, KAFKA_GROUPID
        threading.Thread.__init__(self)
        self.monitor_config = monitor_config
        self.output_data_topic = output_data_topic
        self.monitor_name = monitor_config.get('monitor_name')
        self.running = False
        self.condition = threading.Condition()  # used to interrupt sleep when config changes

        # Kafka settings
        self.consumer = Consumer({
            'bootstrap.servers': f'{KAFKA_HOST}:{KAFKA_PORT}',
            'group.id': KAFKA_GROUPID,
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(topics=[self.monitor_config.get('monitor_name')], on_revoke=self._on_revoke)
        partitions = [TopicPartition(self.monitor_config.get('monitor_name'), p, OFFSET_END) for p in range(3)]
        self.consumer.assign(partitions)

    def get_condition(self) -> threading.Condition:
        """
        Return the thread condition.  Using the condition, another class can interrupt a sleeping thread
        by first acquiring the condition, then notifying and finally releasing.
        c = get_condition()
        c.acquire()
        c.notify()
        c.release()
        :return: the thread condition
        """
        return self.condition

    def _on_revoke(self, consumer, partitions) -> (Consumer, list):
        """
        Kafak will revoke the consumer occasionally.  When this happens, a new consumer is setup
        to allow uninterrupted communications.  This function is only intended to be called via
        the consumer's 'on_revoke' parameter.
        :param consumer:
        :param partitions:
        :return:
        """
        if not self.running:
            return
        logger.error(f"{self.__class__.__name__:25}: subscriber on_revoke triggered.  Resetting consumer.")
        self.consumer.subscribe(topics=[self.monitor_config.get('monitor_name')], on_revoke=self._on_revoke)
        partitions = [TopicPartition(self.monitor_config.get('monitor_name'), p, OFFSET_END) for p in range(3)]
        self.consumer.assign(partitions)
        return consumer, partitions

    def start(self) -> dict:
        """
        Overriding Threading.start() so that we can test if the service is
        already active and set the 'running' variable.
        :return: A dict with bool 'success' and string 'message' describing result.
        """
        if self.running:
            message = {'message': f"[{self.__class__.__name__}]: already running for'{self.monitor_name}'"}
            return message
        try:
            self.running = True
            threading.Thread.start(self)
            message = {'message': f"[{self.__class__.__name__}]: started for '{self.monitor_name}'"}
            return message
        except Exception as e:
            raise Exception(f"[{self.__class__.__name__}]: could not start for '{self.monitor_name}': {e}")

    def stop(self):
        """
        Stop the thread by setting the self.running variable to False.
        :return:
        """
        self.running = False

    def report_status(self):
        return {'class_name': self.__class__.__name__, 'running': self.running, 'is_alive': self.is_alive()}

    def poll_kafka(self, timeout=0):
        """
        Attempt to retrieve any new messages from the consumer's channel.
        Any messages received are checked for configuration changes which are applied.
        :param timeout: Amount of time (in milliseconds) that the poll should wait for a message before continuing
        :return: None
        """
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

    def keep_alive(self):
        pass

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
            if kwargs_list:
                kwargs = {p['field']: p['value'] for p in kwargs_list}
            else:
                kwargs = None

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
                logger.error(f"{self.__class__.__name__}: e")

    def set_value(self, kwargs):
        """
        Updates the k,v pair in the monitor_config.  k, v pairs are expected to be 'field_name', 'value'
        where the 'field_name' is a value in the monitor_config.  If the 'field_name' doesn't exist in
        the monitor_config, it is added.  If it already exists, it is updated.
        :param kwargs: k,v pairs representing the 'field_name' and 'value' to update or add to the monitor_config attribute.
        :return: None
        """
        logger.info(f"{self.__class__.__name__}: setting value: {kwargs}")
        for field, value in kwargs.items():
            self.monitor_config.update({field: value})
        return
