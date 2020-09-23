# kafka-client
A javascript client for kafka

## Why the client

The purpose of this client has been to get hands on experience with kafka.

This client does not interact with Kafka directly but relies on kafka-node for this interaction.
It is more focused on simplifying the API interface rather than the technical with a kafka cluster.
There are other node libraries to interact with kafka such as node-rdkafka.  
By using this client it will possible to switch to using a different kafka interaction package in the future without having to change upstream code.  For instance if kafka-rdnode evolves faster than kafka-node

## Getting started

[see Getting Started](./GettingStarted.md)


## Get a client
```
var client = await client.connect();
```

## View Topics
```
var topics = await client.getTopics();
```

## Creating a Topic
```
await client.createTopic(topic);
```

## Produce a simple message
```
await client.produce(key,value,topic);								
```

## Consuming a message
```
//Establish a message consumer for a group on a topic
var consumeMessage = await client.singleMessageConsumer(group,topic);

//Then wait for a message
var result = await consumeMessage();
```

## Useful Reference

[Getting Started with Kafka Client](https://www.confluent.io/blog/tutorial-getting-started-with-the-new-apache-kafka-0-9-consumer-client/)

## Release Notes
[Release Notes](./RELEASE.md)

