import logging

from traffic_monitor.services.monitor_service import MonitorService


class ActiveMonitors:
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

        def add(self, monitor_name: str, monitor_service: MonitorService):
            if self.is_active(monitor_name):
                return {'success': False, 'message': f"Service for monitor '{monitor_name}' is already active."}
            else:
                self.active_monitors.update({monitor_name: monitor_service})
                return {'success': True, 'message': f"Service for monitor '{monitor_name}' added to active monitors."}

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
