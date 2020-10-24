from abc import ABC, ABCMeta, abstractmethod


class Observer(metaclass=ABCMeta):
    @abstractmethod
    def update(self, data: dict):
        ...


class Observable:
    def __init__(self):
        self.observers = []

    def register(self, observer: Observer):
        self.observers.append(observer)

    def unregister(self, observer: Observer):
        self.observers.remove(observer)

    def notify(self, data: dict):
        for o in self.observers:
            o.update(data)
