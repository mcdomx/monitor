import logging

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
            self.viewing_monitor: MonitorService

        def is_active(self, monitor_name):
            """
            Determine is a named monitor is currently active
            :param monitor_name: Name of monitor
            :return: If active, return the monitor, else return False
            """
            return self.active_monitors.get(monitor_name, False)

        def start(self,
                  monitor_name: str,
                  detector_id: str,
                  feed_id: str,
                  time_zone: str,
                  logged_objects: list = None,
                  notified_objects: list = None,
                  logging_on: bool = True,
                  notifications_on: bool = False,
                  charting_on: bool = False,
                  log_interval: int = 60, detection_interval: int = 5
                  ):
            if self.is_active(monitor_name):
                return {'success': False, 'message': f"Service for monitor '{monitor_name}' is already active."}
            else:
                # create a monitor service and start it
                ms = MonitorService(monitor_name=monitor_name,
                                    detector_id=detector_id,
                                    feed_id=feed_id,
                                    time_zone=time_zone,
                                    logged_objects=logged_objects,
                                    notified_objects=notified_objects,
                                    logging_on=logging_on,
                                    charting_on=charting_on,
                                    notifications_on=notifications_on,
                                    log_interval=log_interval,
                                    detection_interval=detection_interval)

                self.active_monitors.update({monitor_name: ms})
                rv = ms.start()
                return rv

        def stop(self, monitor_name):
            if not self.is_active(monitor_name):
                return {'success': False, 'message': f"Service for monitor '{monitor_name}' is not created nor running."}

            ms: MonitorService = self.active_monitors.get(monitor_name)
            rv = ms.stop()
            if rv['success']:
                self.remove(monitor_name)
            return rv

        def view(self, monitor_name: int):
            ms = self.active_monitors.get(monitor_name)
            if ms is None:
                return {'success': False, 'message': f"MonitorService with is '{monitor_name}' is not active."}

            # if any monitor is currently being viewed, turn it off
            if self.viewing_monitor:
                self.viewing_monitor.display = False

            # set the viewing monitor and set viewing to true
            self.viewing_monitor = monitor_name
            self.viewing_monitor.display = True

            return {'success': True, 'monitor_name': monitor_name}

        def remove(self, monitor_name: str):
            # if removing a monitor that is being viewed stop it
            if self.viewing_monitor:
                if self.viewing_monitor is monitor_name:
                    self.viewing_monitor.display = False
                    self.viewing_monitor = None

            del self.active_monitors[monitor_name]

        def get(self, monitor_name: int):
            ms = self.active_monitors.get(monitor_name)

            if ms is None:
                return {'success': False, 'message': f"Monitor with name '{monitor_name}' is not active."}

            return {'success': True, 'monitor_name': monitor_name}

        def getall(self):
            return self.active_monitors
