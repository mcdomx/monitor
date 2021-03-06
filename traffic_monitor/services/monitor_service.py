"""
This is the top level service for a feed.  This service contains
all the information and supporting services that will execute
a feed, display the feed and log its data.
"""

import queue
import logging
import threading
import json
import time
import os

from confluent_kafka.admin import AdminClient, NewTopic, KafkaException
from confluent_kafka import Consumer, TopicPartition, OFFSET_END, Producer

from traffic_monitor.services.detectors.detector_factory import DetectorFactory
from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.videodetection_service import VideoDetectionService
from traffic_monitor.services.log_service import LogService
from traffic_monitor.services.notification_service import NotificationService
# from traffic_monitor.services.chart_service import ChartService
from traffic_monitor.services.elapsed_time import ElapsedTime

BUFFER_SIZE = 512

logger = logging.getLogger('monitor_service')

SERVICES = {
    'logging_on': LogService,
    'notifications_on': NotificationService,
    # 'charting_on': ChartService,
}

KAFKA_HOST = os.getenv('KAFKA_HOST', '0.0.0.0')
KAFKA_PORT = os.getenv('KAFKA_PORT', 9092)
KAFKA_GROUPID = os.getenv('KAFKA_GROUPID', 'monitorgroup')


class MonitorService(threading.Thread):
    """
    A Monitor is defined as a Detector and a URL video feed.
    The class is a thread that will continually run and log
    data whether the application is displaying the video
    feed or not.

    The Monitor will handle getting streaming images from a
    url and performing detections.  Since detections cannot be
    performed on each frame, the service will determine when
    the detector is ready to perform a new detection and only
    return detection frames when it is able to.

    When running, the feed service will place frames in a queue.
    If the frame includes detections, it will also show the
    detections in the image frame.  If the application is set to
    display the feed from the Monitor, the application can
    get the images to display from the queue of images.

    The MonitorService runs as a thread.  When the thread starts,
    the MonitorService adds itself to the ActiveMonitors singleton.

    ActiveMonitors is a class that hold information about active
    monitors and its largest task is to provide a source for the
    actively running monitors.  The ActiveMonitors class can
    also turn on and off a Monitor's ability to display the visual feed.

    """

    def __init__(self,
                 monitor_config: dict,
                 ):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        # Observer.__init__(self)
        threading.Thread.__init__(self)
        self.id = id(self)

        # LOCAL ATTRIBUTES
        self.monitor_config: dict = monitor_config
        self.monitor_name: str = monitor_config.get('monitor_name')
        self.output_data_topic: str = self.monitor_name
        self.name = f"{self.monitor_name}_thread"
        self.active_services = {}
        self.active_services = {}

        # STATES
        self.running = False
        self.show_full_stream = False
        self.display = False

        # QUEUES
        self.output_image_queue = queue.Queue(BUFFER_SIZE)

        # SETUP KAFKA TOPIC
        # Create a dedicated Kafka topic for this monitor service.
        # This topic is used by the sub-services of this monitor
        # to communicate with each other.
        # https://github.com/confluentinc/confluent-kafka-python
        a = AdminClient({'bootstrap.servers': f'{KAFKA_HOST}:{KAFKA_PORT}',
                         'group.id': KAFKA_GROUPID})
        topic = NewTopic(self.monitor_name, num_partitions=3, replication_factor=1)

        # Call create_topics to asynchronously create topics. {topic,future} is returned.
        fs = a.create_topics([topic])

        # Wait for each operation to finish.
        for t, f in fs.items():
            try:
                f.result()  # The result itself is None
                logger.info("Topic {} created".format(t))
            except KafkaException as e:
                logger.info("Did not create topic {}: {}".format(t, e))
            except Exception as e:
                logger.info("Unhandled error when creating topic {}: {}".format(t, e))

        # Kafka settings
        self.consumer = Consumer({
            'bootstrap.servers': f'{KAFKA_HOST}:{KAFKA_PORT}',
            'group.id': {KAFKA_GROUPID},
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(topics=[self.monitor_config.get('monitor_name')], on_revoke=self._on_revoke)
        partitions = [TopicPartition(self.monitor_config.get('monitor_name'), p, OFFSET_END) for p in range(3)]
        self.consumer.assign(partitions)

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    def get_config(self) -> dict:
        return self.monitor_config

    def _on_revoke(self, consumer, partitions) -> (Consumer, list):
        if not self.running:
            return
        logger.error(f"{self.__class__.__name__:25}: subscriber on_revoke triggered.  Resetting consumer.")
        self.consumer.subscribe(topics=[self.monitor_config.get('monitor_name')], on_revoke=self._on_revoke)
        partitions = [TopicPartition(self.monitor_config.get('monitor_name'), p, OFFSET_END) for p in range(3)]
        self.consumer.assign(partitions)
        return consumer, partitions

    # def get_next_frame(self):
    #     q = self.output_image_queue.get()
    #     return q.get()

    def start_service(self, service_class: ServiceAbstract.__class__):

        service: dict = self.active_services.get(service_class.__name__)

        if service is None:
            s: ServiceAbstract = service_class(
                monitor_config=self.monitor_config,
                output_data_topic=self.output_data_topic,
            )
            s.start()
            self.active_services.update({s.__class__.__name__: {'object': s, 'condition': s.get_condition()}})

    def report_status(self):
        logger.info("SERVICE STATUS REPORT")
        for c, s in self.active_services.items():
            logger.info(f"{c:25}: {s['object'].report_status()}")

    def stop_service(self, service_name):
        service: dict = self.active_services.get(service_name)

        if service is not None:
            s: ServiceAbstract = service.get('object')
            s.stop()
            s.join()
            self.active_services.pop(service_name)

    def start(self):
        """
        Overriding Threading.start() so that we can test if a monitor service  is already active for
        the monitor and set the 'running' variable.
        :return: A dict with bool 'success' and string 'message' describing result.
        """
        if self.running:
            message = {'message': f"[{self.__class__.__name__}] Service is already running: {self.monitor_name}"}
            return message
        try:
            # Start Services
            self.start_service(VideoDetectionService)
        except Exception as e:
            raise Exception(
                f"[{self.__class__.__name__}] Could not start '{self.monitor_name}' VideoDetectionService: {e}")

        for s, c in SERVICES.items():
            if self.monitor_config.get(s):
                try:
                    self.start_service(c)
                except Exception as e:
                    raise Exception(
                        f"[{self.__class__.__name__}] Could not start '{self.monitor_name}' '{c.__name__}': {e}")

        # now that all the monitor's sub-services are started, start the monitor service
        self.running = True
        threading.Thread.start(self)

        return

    def stop(self) -> dict:
        # stop all sub-services
        for s in self.active_services.copy():
            self.stop_service(s)
        message = {'message': f"[{self.__class__.__name__}] Stopped."}
        self.running = False
        logger.info(message.get('message'))
        return message

    def toggle_service(self, kwargs):
        """
        :param kwargs: 'field'=service  'value'=True or False (for on/start or off/stop)
        :return:
        """
        service = kwargs.get('field')
        new_status = kwargs.get('value')
        logger.info(f"I am toggling a service: {service} {new_status}")
        if service not in SERVICES.keys():
            raise Exception(f"'{service}' is not a supported service: {SERVICES.keys()}")
        # update the configuration setting locally
        self.monitor_config.update({service: new_status})

        # start or stop
        if new_status:
            self.start_service(SERVICES.get(service))
        else:
            self.stop_service(SERVICES.get(service))

    def handle_message(self, msg):
        msg_key = msg.key().decode('utf-8')

        # If a config_change message is received, get each service's
        # condition and notify so that the service's run loop
        # is interrupted and the kafka message is checked by the
        # service's abstract class immediately.
        # We also need to make sure the consumers get any
        # keep_alive messages.
        if msg_key == 'config_change' or msg_key == 'keep_alive':
            for s_dict in self.active_services.values():
                c: threading.Condition = s_dict.get('condition')
                if c:
                    c.acquire()
                    c.notify()
                    c.release()

        # toggling a service triggers a config_change, but also requires and action
        # to be fulfilled, this is why the monitor_factory will also send a toggle_service
        # message which contains the function_name and kwargs to execute in order
        # to turn the service on or off in addition to the changed value of the configuration.
        if msg_key == 'toggle_service':

            msg_value = json.JSONDecoder().decode(msg.value().decode('utf-8'))
            function_name = msg_value.get('function')

            # kwargs is a list of two-element dicts with 'field' and 'value' keys.
            # These are converted into a single dict to be used as a kwargs parameter
            # when calling the respective function named in the message.
            kwargs: dict = msg_value.get('kwargs')

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

                # no need to update front-end - this is handled by the
                # monitor_factory when it sends out a config_change message

            except AttributeError as e:
                logger.error(e)

    def run(self):
        """
        The monitor service thread runs with the purpose of reporting sub-thread status'
        and waking up sleeping threads for configuration changes.
        """
        logger.info(f"[{self.__class__.__name__}] Service started for: {self.monitor_name}")

        # timer = ElapsedTime()

        while self.running:

            # report status of service
            # if timer.get() >= 600:
            #     self.report_status()
            #     timer.reset()

            # poll kafka for messages that control the state of services
            msg = self.consumer.poll(0)

            if msg is None:
                pass
            else:
                if msg.error():
                    logger.error(f"[{self.__class__.__name__}] Consumer error: {msg.error()}")
                else:
                    self.handle_message(msg)

            time.sleep(1)

        self.consumer.close()
        logger.info("MONITOR SERVICE HAS STOPPED!")

    @staticmethod
    def get_trained_objects(detector_name) -> list:
        return DetectorFactory().get_trained_objects(detector_name)
