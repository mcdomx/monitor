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
        """
        Publish data to observers of a subject.
        A tuple(2) is published where the first element
        is the subject name and the second is the context.
        The context is expected to be a k.v pair where the
        key is the name of the function in the observer to call
        and the value is the argument to pass to that function.
        :param context:
        :return:
        """
        for o in self.observers:
            o.update((self.subject_name, context))
