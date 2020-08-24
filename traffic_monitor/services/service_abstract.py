import threading
from traffic_monitor.services.observer import Subject, Observer
from abc import ABCMeta, abstractmethod


class ServiceAbstract(threading.Thread, Subject, Observer, metaclass=ABCMeta):

    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        Subject.__init__(self)
        Observer.__init__(self)

    @abstractmethod
    def stop(self):
        ...
