from abc import ABC, abstractmethod


class Observer(ABC):
    def __init__(self):
        self.slug = None

    @abstractmethod
    def update(self, subject_info: tuple):
        ...


class Subject(ABC):
    def __init__(self):
        self.observers: list = []
        self.subject_name: str = ''

    def register(self, observer: Observer):
        self.observers.append(observer)
        return self.subject_name

    def publish(self, context):
        for o in self.observers:
            o.update((self.subject_name, context))
