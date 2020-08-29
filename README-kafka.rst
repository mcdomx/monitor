This project includes docker-compose entries to start zookeeper and kafka.

1. Install kafka

::

    brew install kafka

2. Start Services

a. OPTION 1 - Docker:

::

        monitor/infrastructure.docker-compose up

b. OPTION 2 - Local:

- Start zookeeper. Zookeeper acts like a default gateway for Kafka services.

::

    zookeeper-server-start zookeeper.properties

- Zookeeper binds to: 127.0.0.1:2181
- Bootstrap server binds to: 127.0.0.1:9092

- Start the Kafka server. The Kafka server runs the messaging services including the topics and the partitions that they publish data to.

::

    kafka-server-start server.properties

3. You can now setup topics.

::

    kafka-topics --zookeeper 127.0.0.1:2181 --topic <topic name> --create --partitions 3 --replication-factor 1

You can only have as many replications as you have brokers.

You can list the topics:

::

    kafka-topics --zookeeper 127.0.0.1:2181 --list

and see the configuration of a specific topic

::

    kafka-topics --zookeeper 127.0.0.1:2181 --topic <topic name> --describe

4. Pubish data. Once these two services are running, you can publish and consume data form the kafka-console-producer and kafka-console-consumer.



::

    kafka-console-producer --topic <topic name> --bootstrap-server 127.0.0.1:9092 --producer-property acks=all

Once this is started, you can enter stream entries into the console.  Stop the open stream with crtl-C.

This will require acknowledgements and guarantee that items are written to the message queue

Publishing to a topic name that doesn't exist will create a topic with default values which cab be changed in the kafka config settings.  It is advised to create topics explicitly to ensure that settings are known.

5. Consume data

::

    kafka-console-consumer --topic <topic_name> --bootstrap-server 127.0.0.1:9092 (--from-beginning)

This will stream data from any producer to the topic.  The stream can be stopped using crtl-C.