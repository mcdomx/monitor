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
        timestamp = t.strftime(f"%D %T {tz.tzname(t)}")
        self.send(text_data=json.dumps({'monitor_id': text_data.get('monitor_id'),
                                        'timestamp': str(timestamp),
                                        'counts': text_data.get('counts')}))


class ChartConsumer(WebsocketConsumer):

    def connect(self):
        consumers.update({self.scope.get('path'): self})
        self.logger = logging.getLogger('channel')
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        self.logger.info("Chart Channel got information:")
        self.logger.info(text_data)

    def update(self, text_data=None, bytes_data=None, close=False):
        self.send(text_data=json.dumps({'monitor_id': text_data.get('monitor_id')}))

    def disconnect(self, code):
        self.logger.info("Chart Channel Closed!")
