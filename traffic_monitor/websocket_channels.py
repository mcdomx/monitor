"""
Channels are used to communicate between the Django backend and the web client front-end.
A channel is created by the web-client with the creation of a WebSocket object.

const socket = new WebSocket('ws://' + window.location.host + '/' + <socket_address> + '/')

After the web-client establishes this socket, communication between the back and front-ends
can be done over the specified address.  In this application, the websocket is used
to communicate from the back-end to the front-end.  Communication from the front-end to the
back-end is done via REST calls.

Each service below must have a corresponding route in the traffic_monitor/channel_routing.py file.

"""
import json
import logging
from channels.generic.websocket import WebsocketConsumer

consumers = {}


class ChannelFactory:
    """
    Retrieve an existing consumer via the url for the socket.
    """
    @staticmethod
    def get(url):
        return consumers.get(url)

    @staticmethod
    def get_all():
        return consumers


class ConfigChange(WebsocketConsumer):
    def connect(self):
        consumers.update({self.scope.get('path'): self})
        self.logger = logging.getLogger('channel')
        self.logger.info("STARTING CONFIG UPDATE CHANNEL")
        self.accept()

    def disconnect(self, code):
        self.logger.info("Config Update Channel Closed!")

    def update(self, text_data=None, bytes_data=None, close=False):
        self.send(text_data=json.dumps(text_data))


class ServiceToggle(WebsocketConsumer):
    def connect(self):
        consumers.update({self.scope.get('path'): self})
        self.logger = logging.getLogger('channel')
        self.logger.info("STARTING SERVICE TOGGLE CHANNEL")
        self.accept()

    def disconnect(self, code):
        self.logger.info("Service Toggle Channel Closed!")

    def update(self, text_data=None, bytes_data=None, close=False):
        self.send(text_data=json.dumps(text_data))


class LogChannel(WebsocketConsumer):
    """
    Create a Channels-Redis consumer for logging.  The backend
    can send messages by calling update() and the front end
    can connect to this consumer via a WebSocket.
    """

    def connect(self):
        """
        connect() is called when the web-client creates a WebSocket object.
        The creation of a WebSocket object will automatically call this function
        with a 'scope' parameter which includes the 'path' of the socket.
        To create a channel, the web-client should use JavaScript to instantiate
        a WebSocket object:

        const socket = new WebSocket('ws://' + window.location.host + '/' + <socket_address> + '/')

        After this is created, the back-end can send messages to the front-end by
        calling update() on the channel object created here.

        :return:
        """
        consumers.update({self.scope.get('path'): self})
        self.logger = logging.getLogger('channel')
        self.logger.info("STARTING LOG CHANNEL")
        self.accept()

    def disconnect(self, code):
        self.logger.info("Log Channel Closed!")

    def update(self, text_data=None, bytes_data=None, close=False):
        t = text_data.get('timestamp')
        # tz = t.tzinfo
        # timestamp = t.strftime(f"%D %T {tz.tzname(t)}")
        timestamp = t.strftime(f"%D %T")
        self.send(text_data=json.dumps({'monitor_name': text_data.get('monitor_name'),
                                        'timestamp': str(timestamp),
                                        'counts': text_data.get('counts')}))


class ChartChannel(WebsocketConsumer):

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
