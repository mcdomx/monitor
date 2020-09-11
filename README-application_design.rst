Application Design
==================
The Monitor application uses a variety of frameworks and libraries.  The API and Web server is built using Django driving Python as the primary development language in tis project.

Communication is done using both Kafka and Channels-Redis.

Charting is achieved using Bokeh.

The application uses a Service Oriented Architecture.  The initial releases of this application don't strictly adhere to a microservices concept, but each application component is designed with the intention of making tha application a complete microservice in the future where each component executes in an independent Docker container.


Communications
--------------
Three technologies are used for communicating between components.  Kafka is used for communications between backend components. Channels (sockets) are used to communicate from Django to the web-client and rest calls are used by the web-client to communicate to Django.

Django <-> Django : Kafka

Django --> Web-Client : Channels

Web-Client --> Django : Rest

Kafka
-----
https://docs.confluent.io/current/clients/confluent-kafka-python

The python library confluent-kafka is used to realize Kafak communucation between back-end components.

Channels-Redis
--------------
https://channels.readthedocs.io/en/latest/introduction.html

Channels-Redis is a Django-specific support application that is used in this application to communicate from the web-server to the web-client.

Setting up the channels for communication only requires a few steps but the distributed nature of any communication structure can make it seem complicated:

1. Backend: the channel objects are setup in the traffic_monitor/websocket_channels.py script.  These are the backend Python objects that represent the backend connection to the socket.  Each socket gets a routing through which the back-end and front-end will communicate with each other.  These routings are defined in the traffic_monitor/channel_routing.py file and a top-level routing is defined in the monitor/channel_routing.py file.  Only the traffic_monitor/channel_routing.py file needs to be maintained for new socket urls.


2. Front-End: The channel end of the socket is established by creating an object in JavaScirpt:

::

    const socket = new WebSocket('ws://' + window.location.host + '/ws/traffic_monitor/log/')

To create a new communication channel that the web-client should respond to:

1. Update websocket_channels.py.

If a new type of communication is required, add a new WebSocketConsumer class.  Use the previously created classes as a template for the new class.

2. Update traffic_monitor/channel_routing.py.

Add a websocket path and the respective class that was created in step 1.  Use previous entries as an example.

3. Update the HTML file's JavaScript so that it subscribes to the channel by creating a WebSocket object:

::

    const socket = new WebSocket('ws://' + window.location.host + <websocket_path> + monitor_name + '/')

In this JavaScript you can accept and handle incoming messages by assigning a function socket.onmessage:

::

    socket.onmessage = function(message) {
        const value = JSON.parse(message.data).<key>}
