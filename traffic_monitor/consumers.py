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
        self.logger.info("Sending log data ... ")
        t = text_data.get('timestamp')
        tz = t.tzinfo
        timsstamp = t.strftime(f"%D %T {tz.tzname(t)}")
        self.send(text_data=json.dumps({'timestamp': str(timsstamp),
                                              'counts': text_data.get('counts')}))


class URLConsumer(WebsocketConsumer):

    def connect(self):
        consumers.update({self.scope.get('path'): self})
        self.logger = logging.getLogger('channel')
        self.accept()

    # when receiving new URL, respond with updates URL as confirmation
    def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        print(self.scope)
        message = text_data_json['url']
        self.logger.info(message)
        print(json.dumps({'url': message}))

        self.send(text_data=json.dumps({'url': message}))

    def disconnect(self, code):
        pass
