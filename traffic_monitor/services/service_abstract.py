import threading
from traffic_monitor.services.observer import Subject
from abc import ABCMeta, abstractproperty, abstractmethod


class ServiceAbstract(threading.Thread, Subject, metaclass=ABCMeta):

    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        Subject.__init__(self)

    @abstractmethod
    def stop(self):
        ...
