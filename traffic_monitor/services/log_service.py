"""
This service will monitor a queue for entries that should be
logged. The service will summarize entries after a specified
time interval and save the entries to database.
"""

import logging
import json
import datetime
import pytz
from abc import ABC

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Min, Max, Count

from traffic_monitor.models.model_logentry import LogEntry
from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.elapsed_time import ElapsedTime
from traffic_monitor.websocket_channels import LogChannel, LogDataChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory


logger = logging.getLogger('log_service')


class LogService(ServiceAbstract, ABC):
    """
    An instance of a log service will create entries into the database on a specified interval.
    The LogService operates as a thread and sleeps until the logging interval is complete.
    Once ready to create the log entry, the LogService will look for detections in a
    referenced queue, clearing the queue and writing the detections from that queue
    into the database.

    The LogService will use Kafak to communicate across the back-end and Channels to
    communicate with the front-end.
    """

    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str
                 ):
        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.subject_name = f"logservice__{monitor_config.get('monitor_name')}"
        # self.log_interval = 120  # freq (in sec) in detections are logged
        self.channel_url = f"/ws/traffic_monitor/log/{monitor_config.get('monitor_name')}/"  # websocket channel address
        self.logdata_channel_url = f"/ws/traffic_monitor/logdata/{monitor_config.get('monitor_name')}/"
        self._update_logdata_channel()  # update the logdata before starting

    def handle_message(self, msg) -> (str, object):
        msg_key = msg.key().decode('utf-8')

        if msg_key == 'detector_detection':
            msg_value = json.JSONDecoder().decode(msg.value().decode('utf-8'))

            return msg_key, msg_value

    def _update_log_channel(self, time_stamp, interval_counts_dict):
        log_channel: LogChannel = ChannelFactory().get(self.channel_url)
        # only use the channel if a channel has been created
        if log_channel:
            # this sends message to ay front end that has created a WebSocket
            # with the respective channel_url address
            msg = {'time_stamp': time_stamp,
                   'monitor_name': self.monitor_name,
                   'counts': interval_counts_dict}
            log_channel.send(text_data=DjangoJSONEncoder().encode(msg))

    def _update_logdata_channel(self):
        logdata_channel: LogDataChannel = ChannelFactory().get(self.logdata_channel_url)
        if logdata_channel:
            # get the LogEntry statistics
            _filter = LogEntry.objects.filter(monitor__name='MyMonitor')
            earliest_date = list(_filter.aggregate(Min('time_stamp')).values())[0].strftime("%Y-%m-%d %H:%M:%S %Z")
            latest_date = list(_filter.aggregate(Max('time_stamp')).values())[0].strftime("%Y-%m-%d %H:%M:%S %Z")
            num_records = list(_filter.aggregate(Count('time_stamp')).values())[0]

            msg = {'earliest_log_date': earliest_date,
                   'latest_log_date': latest_date,
                   'num_log_records': num_records}
            logdata_channel.send(text_data=DjangoJSONEncoder().encode(msg))

    def run(self):
        timer = ElapsedTime()
        capture_count = 0
        log_interval_detections = []

        logger.info(f"Starting log service for {self.monitor_name} .. ")
        while self.running:

            msg = self.poll_kafka(0)
            if msg is not None:
                key_msg = self.handle_message(msg)
                if key_msg is not None:
                    msg_key, msg_value = key_msg

                    logger.info(f"Log Service is handling message for {self.monitor_name}:")
                    logger.info(f"\tKEY: {msg_key}")
                    logger.info(f"\tMSG: {msg_value}")

                # the log service will capture data from detector_detection messages
                # if msg_key != 'detector_detection':
                    # time_stamp_type, time_stamp = msg.timestamp()

                    capture_count += 1
                    log_interval_detections += msg_value

            # if the time reached the the logging interval
            if timer.get() >= self.monitor_config.get('log_interval'):
                # Counts the mean observation count at any moment over the log interval period.
                # Only count items that are on the logged_objects list
                objs_unique = set(log_interval_detections)
                interval_counts_dict = {obj: round(log_interval_detections.count(obj) / capture_count, 3) for obj in
                                        objs_unique if obj in self.monitor_config.get('log_objects')}
                # time is saved in UTC
                # time_stamp = datetime.datetime.utcfromtimestamp(time_stamp / 1000)
                time_stamp = datetime.datetime.utcnow()

                # add observations to database
                LogEntry.add(time_stamp=time_stamp,
                             monitor_name=self.monitor_name,
                             count_dict=interval_counts_dict)
                logger.info(f"Monitor: {self.monitor_name} Logged Detections: {interval_counts_dict}")
                logger.info(f"Monitor: {self.monitor_name} Did not log: {[x for x in objs_unique.difference(set(self.monitor_config.get('log_objects')))]}")

                # send web-client updates using the Channels-Redis websocket
                self._update_log_channel(time_stamp, interval_counts_dict)

                # Send the logging database statistics to the front end
                self._update_logdata_channel()

                # reset variables for next observation
                log_interval_detections.clear()
                capture_count = 0
                timer.reset(start_time=timer.start_time+self.monitor_config.get('log_interval'))
                continue

            # only sleep if there wasn't a message and we are reasonable
            # certain there aren't additional messages waiting to be polled
            if msg is None:
                self.condition.acquire()
                self.condition.wait(1)
                self.condition.release()

        self.consumer.close()
        logger.info(f"[{self.monitor_name}] Stopped log service.")
