import json
import logging
from channels.generic.websocket import WebsocketConsumer

consumers = {}


class ConsumerFactory:

    @staticmethod
    def get(url):
        return consumers.get(url)

    @staticmethod
    def get_all():
        return consumers


class LogConsumer(WebsocketConsumer):

    def connect(self):
        consumers.update({self.scope.get('path'): self})
        self.logger = logging.getLogger('channel')
        self.logger.info("STARTING LOG CHANNEL")
        self.accept()

    def disconnect(self, code):
        self.logger.info("Log Channel Closed!")

    def update(self, text_data=None, bytes_data=None, close=False):
        t = text_data.get('timestamp')
        tz = t.tzinfo
        timsstamp = t.strftime(f"%D %T {tz.tzname(t)}")
        self.send(text_data=json.dumps({'monitor_id': text_data.get('monitor_id'),
                                        'timestamp': str(timsstamp),
                                        'counts': text_data.get('counts')}))


class ChartConsumer(WebsocketConsumer):

    def connect(self):
        consumers.update({self.scope.get('path'): self})
        self.logger = logging.getLogger('channel')
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        pass

    def update(self, text_data=None, bytes_data=None, close=False):
        pass

    def disconnect(self, code):
        pass
