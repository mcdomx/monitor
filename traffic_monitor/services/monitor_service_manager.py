import logging

from traffic_monitor.models.monitor_factory import MonitorFactory
from traffic_monitor.services.monitor_service import MonitorService
from traffic_monitor.services.log_service import LogService
from traffic_monitor.services.chart_service import ChartService

logger = logging.getLogger('monitor_service_manager')


class MonitorServiceManager:
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
        return cls.singleton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('detector')
            self.active_monitors = {}
            self.viewing_monitor: str = ''

        def is_active(self, monitor_name) -> bool:
            """
            Determine is a named monitor is currently active
            :param monitor_name: Name of monitor
            :return: If active, return the monitor, else return False
            """
            return self.active_monitors.get(monitor_name, False)

        def set_view_status(self, monitor_name: str) -> dict:
            is_active = self.is_active(monitor_name)
            if not is_active:
                return {'success': False, 'message': f"MonitorService with is '{monitor_name}' is not active."}

            # if any monitor is currently being viewed, turn it off
            if self.viewing_monitor:
                self.viewing_monitor.display = False

            # set the viewing monitor and set viewing to true
            self.viewing_monitor = monitor_name
            self.viewing_monitor.display = True

            return {'success': True, 'monitor_name': monitor_name}

        @staticmethod
        def _get_toggled_objects(monitor_name: str, toggle_objects: list, _type: str) -> list:
            # Helper function to toggle items on or off from a current list of objects
            current_objects = MonitorFactory().get_objects(monitor_name, _type)
            remove_these = set(current_objects).intersection(set(toggle_objects))
            rv: list = list(set(current_objects).union(toggle_objects).difference(remove_these))
            return rv

        @staticmethod
        def toggle_objects(monitor_name: str, objects: list, _type: str) -> dict:
            """
            Build a new list of objects based on a list of objects to toggle, turning current
            items off and not current items on.  Validation of objects is handled when
            objects are set using set_objects.
            :param monitor_name: Name of monitor
            :param objects: list objects to toggle
            :param _type: 'log' or 'notification'
            :return:
            """
            # use helper function to determine a new list of objects after toggling
            if type(objects) == str:
                objects = [o.strip() for o in objects.split(",")]

            toggled_objects: list = MonitorServiceManager()._get_toggled_objects(monitor_name, objects, _type=_type)
            return MonitorServiceManager().set_objects(monitor_name, toggled_objects, _type)

        @staticmethod
        def _validate_objects(objects: list, detector_name: str) -> (list, list):
            """
            Determine items that are trained objects

            :param objects: A list that should be split between valid and invalid objects
            :return: Tuple: A list of valid objects and invalid objects
            """
            trained_objects = MonitorService.get_trained_objects(detector_name)

            invalid_objects = set(objects) - set(trained_objects)
            valid_objects = set(objects) - set(invalid_objects)

            return list(valid_objects), list(invalid_objects)

        @staticmethod
        def all_monitors() -> list:
            return MonitorFactory().all_monitors()

        @staticmethod
        def all_feeds() -> list:
            return MonitorFactory().all_feeds()

        @staticmethod
        def create_stream(**kwargs) -> dict:
            return MonitorFactory().create_feed(**kwargs)

        @staticmethod
        def all_detectors() -> list:
            return MonitorFactory().all_detectors()

        @staticmethod
        def get_monitor(name: str) -> dict:
            return MonitorFactory().get(monitor_name=name)

        @staticmethod
        def create_feed(cam: str, time_zone: str, description: str) -> dict:
            return MonitorFactory().create_feed(cam, time_zone, description)

        @staticmethod
        def create_monitor(**kwargs) -> dict:
            """
            Create a monitor.  Requires parameters:
                detector_name: name of detector to use (get available names via /get_detectors)
                detector_model: name of detector model to use (get available models via /get_detectors)
                feed_id: id of feed that the monitor will use (get available feeds via /get_streams)
                log_objects: comma separated list of objects that the monitor should log
                notification_objects: comma separated list of objects that the monitor will notify

            Log and notification objects will be validated.  A valid list of objects can be retrieved via
            get_trained_objects/detector_name={{detector_name}}
            :param kwargs:
            :return:
            """
            # convert string to lists for log and notification objects

            # validate log and notification lists
            invalid_log_objects = []
            invalid_not_objects = []
            if kwargs.get('log_objects'):
                if type(kwargs.get('log_objects')) == str:
                    kwargs.update({'log_objects': [o.strip() for o in kwargs.get('log_objects').split(",")]})
                log_objects, invalid_log_objects = MonitorServiceManager()._validate_objects(kwargs.get('log_objects'),
                                                                                             kwargs.get(
                                                                                                 'detector_name'))
                kwargs.update({'log_objects': log_objects})

            if kwargs.get('notification_objects'):
                if type(kwargs.get('notification_objects')) == str:
                    kwargs.update(
                        {'notification_objects': [o.strip() for o in kwargs.get('notification_objects').split(",")]})
                notification_objects, invalid_not_objects = MonitorServiceManager()._validate_objects(
                    kwargs.get('notification_objects'), kwargs.get('detector_name'))
                kwargs.update({'notification_objects': notification_objects})

            rv = MonitorFactory().create(**kwargs)

            # create return messages that identify untrained items that were included in lists
            if len(invalid_log_objects) > 0:
                message = {'message_log': f"Untrained log objects are not considered: {invalid_log_objects}"}
                logger.warning(message)
                rv = {**message, **rv}

            if len(invalid_not_objects) > 0:
                message = {'message_not': f"Untrained notification objects are not considered: {invalid_not_objects}"}
                logger.warning(message)
                rv = {**message, **rv}

            return rv

        @staticmethod
        def get_trained_objects(monitor_name: str = None, detector_name: str = None) -> list:
            """
            Retrieve a set of objects that the named detector or monitor has been
            trained to detect. Either the monitor name or detecror name must be provided.
            If both are provided, the monitor name is used.
            :param detector_name: Name of detector
            :param monitor_name: String name of the monitor.
            :return: A set of the objects that are trained.
            """
            if monitor_name is None and detector_name is None:
                raise Exception("Either a 'monitor_name' or a 'detector_name' must be provided.")

            if monitor_name is not None:
                detector_name = MonitorFactory().get_detector_name(monitor_name)

            return MonitorService.get_trained_objects(detector_name)

        @staticmethod
        def get_objects(monitor_name: str, _type: str) -> list:
            return MonitorFactory().get_objects(monitor_name, _type)

        @staticmethod
        def set_objects(monitor_name: str, objects: list, _type: str):
            # validate objects
            detector_name = MonitorFactory().get_detector_name(monitor_name)
            valid_objects, invalid_objects = MonitorServiceManager()._validate_objects(objects, detector_name)

            objects = MonitorFactory().set_objects(monitor_name, valid_objects, _type)

            rv = {'objects': objects}

            if invalid_objects:
                message = {'message': f"Untrained objects are not considered: {invalid_objects}"}
                rv = {**message, **rv}

            return rv

        @staticmethod
        def _get_services_from_config(monitor_config: dict) -> list:
            services = []
            if monitor_config['logging_on']:
                services.append(LogService)
            if monitor_config['charting_on']:
                services.append(ChartService)
            if monitor_config['notifications_on']:
                pass

            return services

        def start_monitor(self,
                          monitor_name: str,
                          log_interval: int,
                          detection_interval: int,
                          charting_interval: int) -> dict:

            try:
                monitor_config = MonitorFactory().get_monitor_configuration(monitor_name)

                # check if the monitor is already active
                if self.is_active(monitor_config.get('monitor_name')):
                    message = {'message': f"[{__name__}] '{monitor_config.get('monitor_name')}' is already active."}
                    return {**message, **monitor_config}

                ms = MonitorService(monitor_config=monitor_config,
                                    services=self._get_services_from_config(monitor_config),
                                    log_interval=log_interval,
                                    detection_interval=detection_interval,
                                    charting_interval=charting_interval)

                rv = ms.start()
                self.active_monitors.update({monitor_name: ms})

                # register the monitor service with the MonitorFactory to get configuration updates
                MonitorFactory().register(ms)

                return {**rv, **monitor_config}
            except Exception as e:
                logger.error(f"{__name__}: {e}")

        def stop_monitor(self, monitor_name) -> str:
            try:
                ms: MonitorService = self.active_monitors.pop(monitor_name, None)

                # check if the monitor is already active
                if ms is None:
                    raise Exception(f"'{monitor_name}' is not active.")

                # if removing a monitor that is being viewed stop it
                if self.viewing_monitor:
                    if self.viewing_monitor is monitor_name:
                        self.viewing_monitor.display = False
                        self.viewing_monitor = None

                ms.stop()
                return f"Service stopped for {monitor_name}"
            except Exception as e:
                logger.error(f"{__name__}: {e}")

        def get_active_monitors(self) -> {}:
            return {m: self.get_monitor_configuration(m) for m in self.active_monitors}

        @staticmethod
        def get_monitor_configuration(monitor_name: str) -> dict:
            return MonitorFactory().get_monitor_configuration(monitor_name)
