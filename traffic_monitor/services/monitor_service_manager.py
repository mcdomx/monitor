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
        def toggle_logged_object(monitor_name: str, object_name: str) -> list:
            detector_name = MonitorFactory().get_detector_name(monitor_name)
            object_name, _ = MonitorServiceManager()._validate_objects([object_name], detector_name)

            return MonitorFactory().toggle_logged_object(monitor_name=monitor_name,
                                                         object_name=object_name[0])

        @staticmethod
        def toggle_notification_object(monitor_name: str, object_name: str):
            detector_name = MonitorFactory().get_detector_name(monitor_name)
            object_name, _ = MonitorServiceManager()._validate_objects([object_name], detector_name)

            return MonitorFactory().toggle_notification_object(monitor_name=monitor_name,
                                                               object_name=object_name[0])

        @staticmethod
        def _validate_objects(set_objects: list, detector_name: str) -> (list, list):
            """
            Determine items that are trained objects

            :param objects: A list that should be split between valid and invalid objects
            :return: Tuple: A list of valid objects and invalid objects
            """
            trained_objects = MonitorService.get_trained_objects(detector_name)

            invalid_objects = set(set_objects) - set(trained_objects)
            valid_objects = set(set_objects) - set(invalid_objects)
            logger.warning(f"Untrained objects are not considered: {invalid_objects}")
            return list(valid_objects), list(invalid_objects)

        @staticmethod
        def set_log_objects(monitor_name: str, set_objects: list):
            # validate objects
            detector_name = MonitorFactory().get_detector_name(monitor_name)
            valid_objects, invalid_objects = MonitorServiceManager()._validate_objects(set_objects, detector_name)

            return MonitorFactory().set_log_objects(monitor_name, valid_objects)

        @staticmethod
        def set_notification_objects(monitor_name: str, set_objects: list):
            # validate objects
            detector_name = MonitorFactory().get_detector_name(monitor_name)
            valid_objects, invalid_objects = MonitorServiceManager()._validate_objects(set_objects, detector_name)

            return MonitorFactory().set_notification_objects(monitor_name, valid_objects)

        @staticmethod
        def all_monitors() -> list:
            return MonitorFactory().all_monitors()

        @staticmethod
        def all_feeds() -> list:
            return MonitorFactory().all_feeds()

        @staticmethod
        def all_detectors() -> list:
            return MonitorFactory().all_detectors()

        @staticmethod
        def get_monitor(monitor_name: str) -> dict:
            return MonitorFactory().get(monitor_name=monitor_name)

        @staticmethod
        def create_feed(cam: str, time_zone: str, description: str) -> dict:
            return MonitorFactory().create_feed(cam, time_zone, description)

        @staticmethod
        def create_monitor(**kwargs) -> dict:
            # validate log and notification lists
            log_objects, invalid_objects = MonitorServiceManager()._validate_objects(kwargs.get('log_objects'),
                                                                                     kwargs.get('detector_name'))
            notification_objects, invalid_objects = MonitorServiceManager()._validate_objects(
                kwargs.get('notification_objects'), kwargs.get('detector_name'))
            kwargs.update({'log_objects': log_objects})
            kwargs.update({'notification_objects': notification_objects})

            return MonitorFactory().create(**kwargs)

        @staticmethod
        def get_trained_objects(monitor_name: str) -> list:
            """
            Retrieve a set of objects that the named monitor has been
            trained to detect.
            :param monitor_name: String name of the monitor.
            :return: A set of the objects that are trained.
            """
            detector_name = MonitorFactory().get_detector_name(monitor_name)
            return MonitorService.get_trained_objects(detector_name)

        @staticmethod
        def get_logged_objects(monitor_name: str) -> list:
            return MonitorFactory().get_logged_objects(monitor_name)

        @staticmethod
        def get_notification_objects(monitor_name: str) -> list:
            return MonitorFactory().get_notification_objects(monitor_name)

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

        def start_monitor(self, monitor_name: str, log_interval: int, detection_interval: int) -> dict:

            rv = MonitorFactory().get_monitor_configuration(monitor_name)
            if not rv['success']:
                return rv

            monitor_config = rv['configuration']

            # check if the monitor is already active
            if self.is_active(monitor_config.get('monitor_name')):
                return {'success': False,
                        'message': f"Service for monitor '{monitor_config.get('monitor_name')}' is already active."}

            ms = MonitorService(monitor_config=monitor_config,
                                services=self._get_services_from_config(monitor_config),
                                log_interval=log_interval,
                                detection_interval=detection_interval)

            rv = ms.start()
            if rv['success']:
                self.active_monitors.update({monitor_name: ms})

            return rv

        def stop_monitor(self, monitor_name) -> dict:
            # check if the monitor is already active
            if not self.is_active(monitor_name):
                return {'success': False, 'message': f"'{monitor_name}' is not active."}

            # if removing a monitor that is being viewed stop it
            if self.viewing_monitor:
                if self.viewing_monitor is monitor_name:
                    self.viewing_monitor.display = False
                    self.viewing_monitor = None

            ms = self.active_monitors.get(monitor_name)
            ms.stop()
            del self.active_monitors[monitor_name]
            return {'success': True, 'message': f"Service stopped for {monitor_name}"}
