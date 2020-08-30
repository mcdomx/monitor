import threading
import logging
from traffic_monitor.services.observer import Subject, Observer
from abc import ABCMeta, abstractmethod

logger = logging.getLogger('service')


class ServiceAbstract(threading.Thread, Subject, Observer, metaclass=ABCMeta):

    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        Subject.__init__(self)
        Observer.__init__(self)

    @abstractmethod
    def stop(self):
        ...

    # The functions below handle Subject updates
    # Each service is able to handle log and notification
    # updates as long as they have 'log_objects' and or
    # 'notification_objects' attributes.

    def _get_message_info(self, subject_name, subject_info):
        """
        Use recursion to find subject with the provided subject_name.
        :param subject_name: Name of published subject to get data for
        :param subject_info: The information sent by the subject.  The final subject info
        is expected to be a dictionary with k, v pairs that represent a function name
        and a function argument to pass to the function.
        :return:
        """
        if len(subject_info) == 1:
            return {}  # subject name not found anywhere
        elif subject_info[0] == subject_name:
            return subject_info[1]
        else:
            # subject name didn't match, try the next element
            # for s in subject_info:
            if type(subject_info[1]) == tuple:
                return self._get_message_info(subject_name, subject_info[1])

        return {}

    def _handle_update(self, subject_name: str, subject_info: tuple):
        """
        Handle an update for a specified subject name.  If a subject is found,
        a dictionary is expected as the value where the key is the function to
        execute and the value is the argument to the function.  The function is executed
        with the argument.  If the subject name is not found, no action is taken.
        :param subject_name: Name of subject data to retrieve from Subject's update
        :param subject_info: The full data received by the Subject's update
        :return: None
        """
        # get the subject info
        # the result is a k, v entry where the key is a function name
        # and the value is a parameter value to apply to the function
        subject_info: dict = self._get_message_info(subject_name, subject_info)

        # for each service, apply function with attribute if the function
        # is supported by the service
        try:
            for f_name, a_value in subject_info.items():
                if hasattr(self, f_name) and callable(getattr(self, f_name)):
                    func = getattr(self, f_name)
                    if a_value:
                        rv = func(a_value)
                    else:
                        rv = func()
                    logger.info(f"'{self.__class__.__name__}' :UPDATED WITH: {f_name}({a_value}) RV: {rv}")

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}]: {e}")

    def set_objects(self, kwargs):
        """
        This only gets called from _handle_update() and is based on values
        provided in Subject update content to this Observer.
        :param kwargs:
        :return:
        """
        objects = kwargs.get('objects')
        _type = kwargs.get('_type')

        if objects is None or _type is None:
            logger.error(f"[{__name__}] Both 'objects' and '_type' must be in published data.")
            return

        if _type == 'log' and hasattr(self, 'log_objects'):
            setattr(self, 'log_objects', objects)
            return getattr(self, 'log_objects')
        elif _type == 'notification' and hasattr(self, 'notification_objects'):
            setattr(self, 'notification_objects', objects)
            return getattr(self, 'notification_objects')
        else:
            logger.info(f"[{__name__}] No updates were made.")
            return None

