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

from traffic_monitor.websocket_channels_factory import ChannelFactory
from traffic_monitor.models.feed_factory import FeedFactory

logger = logging.getLogger('channel')


class ConfigChange(WebsocketConsumer):
    def connect(self):
        ChannelFactory().add(url=self.scope.get('path'), consumer=self)
        logger.info("STARTING CONFIG UPDATE CHANNEL")
        self.accept()

    def disconnect(self, code):
        ChannelFactory().remove(self.scope.get('path'))
        self.close()
        logger.info("Config Update Channel Closed!")

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
        ChannelFactory().add(url=self.scope.get('path'), consumer=self)
        logger.info("STARTING LOG CHANNEL")
        self.accept()

    def disconnect(self, code):
        ChannelFactory().remove(self.scope.get('path'))
        self.close()
        logger.info("Log Channel Closed!")


class LogDataChannel(WebsocketConsumer):
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
        ChannelFactory().add(url=self.scope.get('path'), consumer=self)
        logger.info("STARTING LOGDATA CHANNEL")
        self.accept()

    def disconnect(self, code):
        ChannelFactory().remove(self.scope.get('path'))
        self.close()
        logger.info("LogData Channel Closed!")


class ChartChannel(WebsocketConsumer):

    def connect(self):
        ChannelFactory().add(url=self.scope.get('path'), consumer=self)
        logger.info("STARTING CHART CHANNEL")
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        logger.info("Chart Channel got information:")
        logger.info(text_data)

    def disconnect(self, code):
        ChannelFactory().remove(self.scope.get('path'))
        self.close()
        logger.info("Chart Channel Closed!")


class NotificationChannel(WebsocketConsumer):

    def connect(self):
        ChannelFactory().add(url=self.scope.get('path'), consumer=self)
        logger.info("STARTING NOTIFICATION CHANNEL")
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        logger.info("Notification Channel got information:")
        logger.info(text_data)

    def disconnect(self, code):
        ChannelFactory().remove(self.scope.get('path'))
        self.close()
        logger.info("Notification Channel Closed!")


class VideoChannel(WebsocketConsumer):

    def connect(self):
        ChannelFactory().add(url=self.scope.get('path'), consumer=self)
        logger.info("STARTING VIDEO CHANNEL")
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        logger.info("Video Channel got information:")
        logger.info(text_data)

    def disconnect(self, code):
        ChannelFactory().remove(self.scope.get('path'))
        self.close()
        logger.info("Video Channel Closed!")


class TestVideoChannel(WebsocketConsumer):

    def connect(self):
        ChannelFactory().add(url=self.scope.get('path'), consumer=self)
        logger.info("STARTING TEST VIDEO CHANNEL")
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        logger.info("Test Video Channel got information:")
        logger.info(text_data)

    def disconnect(self, code):
        ChannelFactory().remove(self.scope.get('path'))
        self.close()
        logger.info("Test Video Channel Closed!")
