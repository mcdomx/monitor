import logging

from traffic_monitor.models.monitor_factory import MonitorFactory
from traffic_monitor.services.monitor_service import MonitorService


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

        # def set_active(self, monitor_name: str, monitor_service: MonitorService):
        #     """
        #     Set a Monitor to active status
        #     :param monitor_name: Name of monitor
        #     :param monitor_service: The service that is currently running for the Monitor
        #     :return: None
        #     """


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

        # def set_inactive(self, monitor_name: str):
        #     if not self.is_active(monitor_name):
        #         return {'success': False, 'message': f"'{monitor_name}' is not active."}
        #
        #     # if removing a monitor that is being viewed stop it
        #     if self.viewing_monitor:
        #         if self.viewing_monitor is monitor_name:
        #             self.viewing_monitor.display = False
        #             self.viewing_monitor = None
        #
        #     del self.active_monitors[monitor_name]
        #     return {'success': True, 'message': f"'{monitor_name}' set to inactive."}

        # def get(self, monitor_name: int):
        #     ms = self.active_monitors.get(monitor_name)
        #
        #     if ms is None:
        #         return {'success': False, 'message': f"Monitor with name '{monitor_name}' is not active."}
        #
        #     return {'success': True, 'monitor_name': monitor_name}

        # def getall(self):
        #     return self.active_monitors

        @staticmethod
        def toggle_logged_object(monitor_name: str, object_name: str):
            trained_objects = MonitorServiceManager().get_trained_objects(monitor_name)
            return MonitorFactory().toggle_logged_object(monitor_name=monitor_name,
                                                         object_name=object_name,
                                                         trained_objects=trained_objects)

        @staticmethod
        def toggle_notification_object(monitor_name: str, object_name: str):
            trained_objects = MonitorServiceManager().get_trained_objects(monitor_name)
            return MonitorFactory().toggle_notification_object(monitor_name=monitor_name,
                                                               object_name=object_name,
                                                               trained_objects=trained_objects)

        @staticmethod
        def set_log_objects(monitor_name: str, set_objects: list):
            trained_objects = MonitorServiceManager().get_trained_objects(monitor_name)
            return MonitorFactory().set_log_objects(monitor_name, set_objects, trained_objects)

        @staticmethod
        def set_notification_objects(monitor_name: str, set_objects: list):
            trained_objects = MonitorServiceManager().get_trained_objects(monitor_name)
            return MonitorFactory().set_notification_objects(monitor_name, set_objects, trained_objects)

        @staticmethod
        def all_monitors() -> dict:
            return MonitorFactory().all_monitors()

        @staticmethod
        def all_feeds() -> dict:
            return MonitorFactory().all_feeds()

        @staticmethod
        def all_detectors() -> dict:
            return MonitorFactory().all_detectors()

        @staticmethod
        def get_monitor(monitor_name: str):
            return MonitorFactory().get(monitor_name=monitor_name)

        @staticmethod
        def create_monitor(name: str, detector_id: str, feed_id: str,
                           log_objects: list,
                           notification_objects: list,
                           logging_on: bool,
                           notifications_on: bool,
                           charting_on: bool):

            return MonitorFactory().create(name=name,
                                           detector_id=detector_id,
                                           feed_cam=feed_id,
                                           log_objects=log_objects,
                                           notification_objects=notification_objects,
                                           logging_on=logging_on,
                                           notifications_on=notifications_on,
                                           charting_on=charting_on)

        @staticmethod
        def get_trained_objects(monitor_name: str):
            """
            Retrieve a set of objects that the named monitor has been
            trained to detect.
            :param monitor_name: String name of the monitor.
            :return: A set of the objects that are trained.
            """
            rv = MonitorFactory().get_detector_name(monitor_name)
            if not rv['success']:
                return rv

            detector_name = rv['name']

            rv = MonitorService.get_trained_objects(detector_name)
            if not rv['success']:
                return set()
            return rv['objects']

        @staticmethod
        def get_logged_objects(monitor_name: str):
            rv = MonitorFactory().get_logged_objects(monitor_name)
            if not rv['success']:
                return rv
            return rv['objects']

        @staticmethod
        def get_notification_objects(monitor_name: str):
            rv = MonitorFactory().get_notification_objects(monitor_name)
            if not rv['success']:
                return rv

            return rv['objects']

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
