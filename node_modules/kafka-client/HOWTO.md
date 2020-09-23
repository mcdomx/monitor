# Questions which to using this client

## How to request latest offset  minus X messages from a topic

It was easy to see how to query from the beginning or from the end of the queue.  By setting the ```fromOffset``` to 'earlest' or 'latest' in the options provided to the ConsumerGroup this was possible.

I was interested to be able to query the latest X messages in a topic queue.

This took quite a long time figure out.
There was a trick required to set the
```fromOffset: true```
option in creating the Consumer. Without this option setting the implementation did not respect setting a target offset.
```
var options = {
  ...,
  fromOffset: true
};
var consumer = new Consumer(client,[{
  topic: topic,
  partition: 0,
  offset: targetOffset
}],options);
```

## How to create a topic with multiple partitions

It seems this is only possible through the kafka shell commands
[see this](https://stackoverflow.com/questions/47139534/how-to-create-kafka-topic-with-partitions-in-nodejs)

## How to retrieve all messages on a compacted  topic

A topic has been created with 
```
kafka-topics.sh --zookeeper ${KAFKA_HOST}:2181 --create --topic atopic --config "cleanup.policy=compact" --config "delete.retention.ms=100" --config "segment.ms=100" --config "min.cleanable.dirty.ratio=0" --partitions 1 --replication-factor 1
```

A number of key values are produced into the topic. Some of the keys where the same.
```
var client = new kafka.KafkaClient({kafkaHost: "<host:port>",autoConnect: true})
var producer = new HighLevelProducer(client);
    producer.send(payload, function(error, result) {
    debug('Sent payload to Kafka: ', payload);
    if (error) {
      console.error(error);
    } else {
      res(true)
    }
    client.close()
  });
});
```
Here are the keys and values inserted
```
key - 1
key2 - 1
key3 - 1
key - 2
key2 - 2
key3 - 2
key1 - 3
key - 3
key2 - 3
key3 - 3
```

Then the set of topic keys was requested.
```
var options = {
        id: 'consumer1',
        kafkaHost: "<host:port>",
        groupId: "consumergroup1",
        sessionTimeout: 15000,
        protocol: ['roundrobin'],
        fromOffset: 'earliest'
      };
      var consumerGroup = new ConsumerGroup(options, topic);
        consumerGroup.on('error', onError);
        consumerGroup.on('message', onMessage);
        consumerGroup.on('done', function(message) {
          consumerGroup.close(true,function(){ });
        })
        function onError (error) {
          console.error(error);
        }
        function onMessage (message) {)
            console.log('%s read msg Topic="%s" Partition=%s Offset=%d HW=%d', this.client.clientId, message.topic, message.partition, message.offset, message.highWaterOffset, message.value);
        }
      })
```
The results are surprising:
```
consumer1 read msg Topic="atopic" Partition=0 Offset=4 highWaterOffset=10 Key=key2 value={"name":"key2","url":"2"}
consumer1 read msg Topic="atopic" Partition=0 Offset=5 highWaterOffset=10 Key=key3 value={"name":"key3","url":"2"}
consumer1 read msg Topic="atopic" Partition=0 Offset=6 highWaterOffset=10 Key=key1 value={"name":"key1","url":"3"}
consumer1 read msg Topic="atopic" Partition=0 Offset=7 highWaterOffset=10 Key=key value={"name":"key","url":"3"}
consumer1 read msg Topic="atopic" Partition=0 Offset=0 highWaterOffset=10 Key= value=
consumer1 read msg Topic="atopic" Partition=0 Offset=0 highWaterOffset=10 Key= value=
consumer1 read msg Topic="atopic" Partition=0 Offset=0 highWaterOffset=10 Key= value=
consumer1 read msg Topic="atopic" Partition=0 Offset=0 highWaterOffset=10 Key= value=
```
There is a high water offset which represents the latest value of 10
However the offset value the consumer sees is only up to 7.
Somehow the compaction prevents the consumer from seeing the latest messages.

Its not clear how to avoid this constraint and allow the connsumer to see the latest messages.