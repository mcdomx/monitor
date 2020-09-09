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
from channels.generic.websocket import WebsocketConsumer

class ChannelFactory:
    """
    Retrieve an existing consumer via the url for the socket.
    """
    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = cls._Singleton()
        return cls.singleton

    class _Singleton:
        def __init__(self):
            self.consumers: dict = {}

        def get(self, url):
            return self.consumers.get(url)

        def get_all(self):
            return self.consumers

        def add(self, url: str, consumer: WebsocketConsumer):
            self.consumers.update({url: consumer})

        def remove(self, url):
            self.consumers.pop(url)
