import logging
import json
import datetime
import os

from confluent_kafka import Producer
from django.db.models import Min, Max, Count
from channels.generic.websocket import WebsocketConsumer

from traffic_monitor.models.model_monitor import Monitor
from traffic_monitor.models.feed_factory import FeedFactory
from traffic_monitor.models.model_logentry import LogEntry
from traffic_monitor.websocket_channels_factory import ChannelFactory

logger = logging.getLogger('monitor_factory')

KAFKA_HOST = os.getenv('KAFKA_HOST', '0.0.0.0')
KAFKA_PORT = os.getenv('KAFKA_PORT', 9092)
KAFKA_GROUPID = os.getenv('KAFKA_GROUPID', 'monitorgroup')


class MonitorFactory:
    global KAFKA_HOST, KAFKA_PORT
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
        return cls.singleton

    class _Singleton:
        def __init__(self):
            self.producer = Producer({'bootstrap.servers': f'{KAFKA_HOST}:{KAFKA_PORT}',
                                      'group.id': KAFKA_GROUPID})

        @staticmethod
        def create_feed(cam: str, time_zone: str, description: str) -> dict:
            return FeedFactory().create(cam, time_zone, description)

        @staticmethod
        def all_monitors() -> list:
            try:
                return list(Monitor.objects.all().values())
            except Exception as e:
                raise Exception(f"Failed to retrieve monitors: {e}")

        @staticmethod
        def all_feeds() -> list:
            return Monitor.all_feeds()

        @staticmethod
        def all_detectors() -> list:
            return Monitor.all_detectors()

        @staticmethod
        def create(name: str, detector_name: str, detector_model: str, feed_id: str,
                   log_objects: list = [],
                   notification_objects: list = [],
                   logging_on: bool = True,
                   notifications_on: bool = False,
                   charting_on: bool = False,
                   charting_objects: list = None,
                   charting_time_horizon: str = '6',
                   charting_time_zone: str = 'UTC',
                   class_colors: dict = None) -> dict:
            """
            Create a Monitor entry which is a combination of detector and feed
            as well as the logged and notified objects.

            :param class_colors:
            :param charting_time_zone:
            :param charting_time_horizon:
            :param charting_objects:
            :param detector_model:
            :param detector_name:
            :param notification_objects:
            :param log_objects:
            :param name: The unique name for the new Monitor
            :param feed_id: The cam id of the feed
            :param charting_on: bool(False) - If True, monitor will provide charting service
            :param notifications_on: bool(False) - If True, monitor will provide notification service
            :param logging_on: bool(True) - If True, monitor will provide logging service
            :return: The new database entry as a Django object
            """
            # If the monitor name already exists, raise exception
            try:
                _ = Monitor.objects.get(pk=name)
                raise Exception(f"Monitor with name '{name}' already exists.")
            except Monitor.DoesNotExist:
                if charting_objects is None:
                    charting_objects = log_objects.copy()
                monitor: Monitor = Monitor.create(name=name,
                                                  detector_name=detector_name,
                                                  detector_model=detector_model,
                                                  feed_id=feed_id,
                                                  log_objects=log_objects,
                                                  notification_objects=notification_objects,
                                                  logging_on=logging_on,
                                                  notifications_on=notifications_on,
                                                  charting_on=charting_on,
                                                  charting_objects=charting_objects,
                                                  charting_time_zone=charting_time_zone,
                                                  charting_time_horizon=charting_time_horizon,
                                                  class_colors=class_colors)

                return monitor.__dict__

        @staticmethod
        def update_monitor(kwargs):

            if len(kwargs) == 1:
                return {'message': f"No records to update for '{kwargs.get('monitor_name')}'"}

            # need to make a copy since kwargs is passed by reference
            monitor: Monitor = Monitor.update_monitor(kwargs.copy())

            # create message
            for field, value in kwargs.items():

                if field == 'monitor_name':
                    continue
                key = 'config_change'
                msg = {
                    'message': f'configuration change for {monitor.name}',
                    'function': 'set_value',
                    'kwargs': [{'field': field, 'value': value}]
                }

                MonitorFactory()._publish_message(monitor.name, key, msg)

            return MonitorFactory().get_monitor_configuration(monitor.name)

        @staticmethod
        def get(monitor_name) -> dict:
            """
            Retrieve a monitor object.

            :param monitor_name: The name of the monitor to retrieve
            :return: A dictionary with keys: 'success', 'message', 'monitor' here monitor is the Django monitor object.
            """
            try:
                return Monitor.objects.get(pk=monitor_name).__dict__
            except Monitor.DoesNotExist:
                raise Exception(f"Monitor with name '{monitor_name}' does not exist.")

        @staticmethod
        def get_detector_name(monitor_name: str) -> str:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.get_detector_name()

        @staticmethod
        def get_objects(monitor_name: str, _type: str) -> list:
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return monitor.get_objects(_type=_type)

        @staticmethod
        def get_value(monitor_name: str, field: str):
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            return getattr(monitor, field)

        def delivery_report(self, err, msg):
            """ Kafka support function.  Called once for each message produced to indicate delivery result.
                Triggered by poll() or flush(). """
            if err is not None:
                logger.info(f'Monitor_Factory Message delivery failed: {err}')
            else:
                logger.info(f'Monitor_Factory Message delivered to {msg.topic()} partition:[{msg.partition()}]')

        def toggle_service(self, monitor_name: str, service: str):
            """
            Toggling a service requires a parameter value to be updated as well as an action to be executed.
            The status of the service is updated and the service needs to be turned on or off.  This function
            will use set_value() to update the argument value and additionally send a message that will
            trigger the monitor service to turn the service on or off.
            :param monitor_name:  Name of monitor that has the service which should be toggled.
            :param service: The service to toggle ('log', 'notification', 'chart')
            :return: The parameter field name and the new value as a tuple
            """
            services = {'log': 'logging_on',
                        'notification': 'notifications_on',
                        'chart': 'charting_on'}

            if service not in services.keys():
                message = f"'{service}' is not supported.  'service' must be one of {services.keys()}"
                logger.error(message)
                return {'error': message}

            field = services.get(service)

            # change the monitor record by flipped boolean
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            new_val = not getattr(monitor, field)
            rv = self.set_value(monitor_name, field, new_val)

            # a config_change message will be published when set_value is called
            # but we also send a toggle_service message since toggling a service
            # not only changes a monitor value, but also drives an action.
            # The monitor_service is the only class that is listening for this
            key = 'toggle_service'
            msg = {
                'message': f"toggle '{service}' for '{monitor_name}'",
                'function': 'toggle_service',
                'kwargs': {'field': field, 'value': new_val}
            }

            # no need to publish to the front-end - the config_change will publish the
            # argument's new value to the front-end
            self._publish_message(monitor_name, key, msg, channel=False)

            return rv

        def set_value(self, monitor_name: str, field: str, value):
            """
            Set the value of model objects
            :param monitor_name:
            :param field:
            :param value:
            :return:
            """
            # remove leading and trailing apostrophes, quotes and spaces
            if type(value) == str:
                value = value.strip().strip("'").strip("\"").strip()
            if type(value) == list:
                value = [v.strip().strip("'").strip("\"").strip() for v in value]

            # update value
            monitor: Monitor = Monitor.objects.get(pk=monitor_name)
            rv = monitor.set_value(field, value)

            # create message
            key = 'config_change'
            msg = {
                'message': f'configuration change for {monitor_name}',
                'function': 'set_value',
                'kwargs': [{'field': field, 'value': value}]
            }

            self._publish_message(monitor_name, key, msg)

            return rv

        def _publish_message(self, monitor_name, key, message, kafka=True, channel=True):

            if kafka:
                # Update backend using Kafka
                # --------------------------
                self.producer.poll(0)
                self.producer.produce(topic=monitor_name,
                                      key=key,
                                      value=json.JSONEncoder().encode(message),
                                      callback=self.delivery_report,
                                      )
                self.producer.flush()
                # --------------------------

            if channel:
                # Update Front-End using Channels
                # -------------------------------
                channel: WebsocketConsumer = ChannelFactory().get(f"/ws/traffic_monitor/{key}/{monitor_name}/")
                # only update the channel if a channel has been created (i.e. - a front-end is using it)
                if channel:
                    logger.info(f"Monitor_Factory sending message to a channel: {monitor_name} {key}")
                    # send message to front-end
                    channel.send(json.JSONEncoder().encode(message))
                else:
                    logger.info(f">>>>> Not a channel channel: /ws/traffic_monitor/{key}/{monitor_name}/")
                # -------------------------------

        @staticmethod
        def get_monitor(monitor_name: str) -> dict:
            return Monitor.objects.get(name=monitor_name).__dict__

        @staticmethod
        def get_monitor_configuration(monitor_name: str, field: str = None) -> dict:

            monitor: Monitor = Monitor.objects.get(name=monitor_name)
            if field is None or field == 'feed_url':
                monitor = monitor.refresh_url()  # urls can go stale - make sure url is current

            field_map: dict = {'monitor_name': monitor.name,
                               'detector_id': monitor.detector.detector_id,
                               'detector_name': monitor.detector.name,
                               'detector_model': monitor.detector.model,
                               'detector_sleep_throttle': monitor.detector_sleep_throttle,
                               'detector_confidence': monitor.detector_confidence,
                               'feed_description': monitor.feed.description,
                               'feed_id': monitor.feed.cam,
                               'feed_url': monitor.feed.url,
                               'time_zone': monitor.feed.time_zone,
                               'log_objects': monitor.log_objects,
                               'notification_objects': monitor.notification_objects,
                               'logging_on': monitor.logging_on,
                               'log_interval': monitor.log_interval,
                               'notifications_on': monitor.notifications_on,
                               'charting_on': monitor.charting_on,
                               'charting_time_horizon': monitor.charting_time_horizon,
                               'charting_objects': monitor.charting_objects,
                               'charting_time_zone': monitor.charting_time_zone,
                               'class_colors': monitor.class_colors}

            if field is None:
                return field_map
            else:
                return {field: field_map.get(field)}

        @staticmethod
        def get_logdata(kwargs) -> dict:
            """
            Returns all available logdata for a monitor.
            :param kwargs:
            :return:
            """
            monitor_name = kwargs.get('monitor_name')
            _filter = {'monitor__name': monitor_name}

            try:
                m = Monitor.objects.get(pk=monitor_name)
            except Monitor.DoesNotExist:
                return {'success': False, 'message': f"'{monitor_name}' does not exist"}
            except Exception as e:
                return {'success': False, 'message': f"'{monitor_name}' -> Unknown error retrieving monitor."}

            try:
                start_date = kwargs.get('start_date', None)
                if start_date:
                    start_date = start_date[:26]
                    start_date = datetime.datetime.fromisoformat(start_date)
                    start_date = datetime.datetime.combine(start_date.date(), start_date.time(),
                                                           tzinfo=datetime.timezone.utc)
                    _filter.update({'time_stamp__gte': start_date})
                else:
                    start_date = kwargs.get('start_date_gt', None)[:26]
                    if start_date:
                        start_date = start_date[:26]
                        start_date = datetime.datetime.fromisoformat(start_date)
                        start_date = datetime.datetime.combine(start_date.date(), start_date.time(),
                                                               tzinfo=datetime.timezone.utc)
                        _filter.update({'time_stamp__gt': start_date})

            except Exception as e:
                return {'success': False, 'message': f"'{monitor_name}' -> Unable to filter arguments."}

            try:
                rs = LogEntry.objects.filter(**_filter)
                if len(rs) > 0:
                    return {'success': True, 'message': list(rs.values('time_stamp', 'class_name', 'count'))}
                else:
                    raise Exception("No entries match criteria.")
            except Exception as e:
                return {'success': False, 'message': f"'{monitor_name}' -> Unable to get Log entries. {e.args}"}

        @staticmethod
        def get_logged_data_csv(kwargs) -> dict:
            """
            Returns the records logged for a monitor will optional filters for 'start_date', 'end_date' and 'objects' applied.
            :param kwargs:
            :return:
            """
            monitor_name = kwargs.get('monitor_name')
            _filter = {'monitor__name': monitor_name}

            try:
                m = Monitor.objects.get(pk=monitor_name)
            except Monitor.DoesNotExist:
                return {'success': False, 'message': f"'{monitor_name}' does not exist"}
            except Exception as e:
                return {'success': False, 'message': f"'{monitor_name}' -> Unknown error retrieving monitor."}

            try:
                start_date = kwargs.get('start_date', None)
                if start_date:
                    start_date = datetime.datetime.fromisoformat(start_date)
                    start_date = datetime.datetime.combine(start_date.date(), start_date.time(),
                                                           tzinfo=datetime.timezone.utc)
                    _filter.update({'time_stamp__gte': start_date})

                end_date = kwargs.get('end_date', None)
                if end_date:
                    end_date = datetime.datetime.fromisoformat(end_date)
                    end_date = datetime.datetime.combine(end_date.date(), end_date.time(), tzinfo=datetime.timezone.utc)
                    _filter.update({'time_stamp__lte': end_date})

                objects = kwargs.get('objects', None)
                if objects:
                    objects = [o.strip() for o in objects.split(",")]
                    _filter.update({'class_name__in': objects})

            except Exception as e:
                return {'success': False, 'message': f"'{monitor_name}' -> Unable to filter arguments."}

            try:
                rs = LogEntry.objects.filter(**_filter)
                return {'success': True, 'message': list(rs.values())}
            except Exception as e:
                return {'success': False, 'message': f"'{monitor_name}' -> Unable to get Log entries. {e.args}"}

        @staticmethod
        def get_logdata_info(monitor_name: str) -> dict:
            """
            Return statistics on the logged data for a specified monitor.

            :param monitor_name: Name of monitor for which data should be retrieved
            :return:
            """
            try:
                Monitor.objects.get(pk=monitor_name)
            except Monitor.DoesNotExist:
                return {'success': False, 'message': f"'{monitor_name}' does not exist."}

            try:
                _filter = LogEntry.objects.filter(monitor__name=monitor_name)
                earliest_date = list(_filter.aggregate(Min('time_stamp')).values())[0].strftime("%Y-%m-%d %H:%M:%S %Z")
                latest_date = list(_filter.aggregate(Max('time_stamp')).values())[0].strftime("%Y-%m-%d %H:%M:%S %Z")
                num_records = list(_filter.aggregate(Count('time_stamp')).values())[0]

                msg = {'earliest_log_date': earliest_date,
                       'latest_log_date': latest_date,
                       'num_log_records': num_records}

                return {'success': True, 'message': msg}
            except Exception as e:
                return {'success': False, 'message': e.args}
