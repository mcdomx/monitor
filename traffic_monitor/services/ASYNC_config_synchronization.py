import logging
import asyncio
import json
from abc import ABCMeta, abstractmethod, ABC

from confluent_kafka import Consumer, TopicPartition, OFFSET_END

logger = logging.getLogger('service')


class MessageConsumer(metaclass=ABCMeta):
    """
    This abstract class enables an inheriting class to receive Kafka messages and will
    keep a 'monitor_config' attribute updated when updates to values are received.

    This class will launch an asynchronous loop that will poll kafka and update
    'monitor_config' when updated values are communicated.

    This abstract class requires an inheriting class to implement a 'handle_message'
    method that should handle messages specific to the inheriting class.

    """

    def __init__(self, topic: str, monitor_config: dict):

        self.monitor_config: dict = monitor_config
        self.topic = topic
        self.running_task = None

        # Kafka settings
        self.consumer = Consumer({
            'bootstrap.servers': '127.0.0.1:9092',
            'group.id': 'monitorgroup',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(topics=[self.topic], on_revoke=self._on_revoke)
        partitions = [TopicPartition(self.topic, p, OFFSET_END) for p in range(3)]
        self.consumer.assign(partitions)

    @abstractmethod
    def handle_message(self, msg) -> (str, object):
        """
        Any class inheriting class should implement this method to handle message of a particular key.
        This class will handle the key 'config_change' and does not need to be implemented.
        :param msg: kafka message object
        :return: tuple of (key, msg value)
        """
        ...

    async def start_polling(self):
        try:
            self.running_task = asyncio.create_task(self.run())
            await self.running_task
        except asyncio.CancelledError:
            logger.info(f"{self.__class__.__name__} was stopped!")

    def stop_polling(self):
        self.running_task.cancel()

    async def run(self):
        try:
            while True:
                self.poll_kafka()
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise

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

        # run the class-specific handler
        self.handle_message(msg)

    def _on_revoke(self, consumer, partitions) -> (Consumer, list):
        """
        Kafak will revoke the consumer occasionally.  When this happens, a new consumer is setup
        to allow uninterrupted communications.  This function is only intended to be called via
        the consumer's 'on_revoke' parameter.
        :param consumer:
        :param partitions:
        :return:
        """
        logger.error(f"{self.__class__.__name__:25}: subscriber on_revoke triggered.  Resetting consumer.")
        self.consumer.subscribe(topics=[self.topic], on_revoke=self._on_revoke)
        partitions = [TopicPartition(self.topic, p, OFFSET_END) for p in range(3)]
        self.consumer.assign(partitions)
        return consumer, partitions

    def _handle_config_change(self, msg):
        """
        This abstract class will handle message with the key 'config_change'.
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


class TestConsumer(MessageConsumer, ABC):

    def __init__(self, topic: str, monitor_config: dict):
        MessageConsumer.__init__(self, topic=topic, monitor_config=monitor_config)

    def handle_message(self, msg) -> (str, object):
        pass
