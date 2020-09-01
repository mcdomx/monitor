from abc import ABC, abstractmethod


class Observer(ABC):
    def __init__(self):
        self.slug = None

    @abstractmethod
    def update(self, context: dict):
        ...


class Subject(ABC):
    def __init__(self):
        self.observers: list = []
        self.subject_name: str = ''

    def register(self, observer: Observer):
        self.observers.append(observer)
        return self.subject_name

    def publish(self, context: dict):
        """

        Publish data to observers of a subject.
        The context is expected to be a dictionary:
        {'subject': 'monitor_config',
         'function': 'set_value',
         'kwargs': {field: value}}

        :param context:
        :return:
        """
        for o in self.observers:
            o.update(context)
