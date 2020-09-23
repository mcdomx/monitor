// This client implementation connects directly to the Kafka nodes directly rather than connecting to Zookeeper
// The configuration only requires connectivity to Kafak and not zookeeper

var kafka = require('kafka-node')
var ConsumerGroup = kafka.ConsumerGroup
var HighLevelProducer = kafka.HighLevelProducer

var Consumer = kafka.Consumer

var debug = require('debug')('kafka-client')

var pkg = require('../package.json')
debug(pkg.version)

const K2Client = function (kafkanodes) {
  var kfnodes = kafkanodes

  return {
    // close: function() {
    //   debug('Closing KafkaClient')
    //   client.close()
    // },
    producePayload: function (payload) {
      return new Promise(function (resolve, reject) {
        var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
        var producer = new HighLevelProducer(client)
            producer.send(payload, function (error, result) {
              debug('Sent payload to Kafka: ', payload)
              if (error) {
                console.error(error)
                reject(error)
              } else {
                resolve(true)
              }
              client.close()
            })
          })
    },
    produceTopicValue: function (value, topic, partition = 0) {
      var payload = [{
        topic: topic,
        partition: partition,
        messages: [JSON.stringify(value)],
        attributes: 0 /* Use GZip compression for the payload */
      }]
      return this.producePayload(payload)
    },
    produceTopicKeyValue: function (key, value, topic) {
      var payload = [{
        key: key,
        topic: topic,
        messages: [JSON.stringify(value)],
        attributes: 0 /* Use GZip compression for the payload */
      }]
      return this.producePayload(payload)
    },
    createTopic: function (topic) {
      // console.log(kfnodes)
      var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
      return new Promise(function (resolve, reject) {
        debug('Creating topics:', topic)
        client.createTopics(topic, true, function (error, results) {
        debug('CreatedTopic:' + results)
          if (!error) {
            resolve(results)
          } else {
            reject(error)
          }
          client.close()
        })
      })
    },
    getTopics: async function () {
      var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
      var result = await new Promise(function (resolve, reject) {
       client.loadMetadataForTopics([], function (error, results) {
         if (error) {
           console.log(error)
           results()
         } else {
          resolve(results)
         }
         client.close()
       })
     })
     return result.map(function (node) {
       return node['metadata'] ? Object.keys(node.metadata) : []
     }).reduce((a, b) => a.concat(b), [])
    },
    getOffset: function (topic) {
      var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
      debug('Get Offset:', topic)
      return new Promise(function (resolve, reject) {
        var offset = new kafka.Offset(client)
        offset.fetch([
          {
            topic,
            time: -1, // not sure why this gives us the latest offsets
            maxNum: 10
          }
        ], function (err, data) {
          if (err) {
            if (err[0] === 'LeaderNotAvailable') {
              resolve(null)
            } else {
              reject(err)
            }
          } else if (data) {
            resolve(data)
          }
          client.close()
        })
      })
    },
    createSubscriber: async function (groupid, topic, messageHandler, fromOffset = 'latest') {
      var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
      var topicOffsets = await this.getOffset(topic)
      var latestOffset = topicOffsets[topic]['0'][0]
      var targetOffset = latestOffset - 1
      var options = {
        autoCommit: true,
        fetchMaxWaitMs: 1000,
        fetchMaxBytes: 1000000,
        fromOffset: true
      }
      var consumer = new Consumer(client, [{
        topic: topic,
        partition: 0,
        offset: targetOffset
      }], options)

      consumer.on('error', onError)
      consumer.on('message', onMessage)
      consumer.on('done', onDone)
      function onError (error) {
        console.error(error)
        console.error(error.stack)
      }
      function onDone (message) {
        debug('Done', message)
        // consumer.close(false,function(){});
      }
      function onMessage (message) {
        if (message.key && message.value.length > 0) {
          debug('%s read msg Topic="%s" Partition=%s Offset=%d highWaterOffset=%d Key=%s value=%s', this.client.clientId, message.topic, message.partition, message.offset, message.highWaterOffset, message.key, message.value)
          messageHandler(JSON.parse(message.value))
        }
      }
      return {
        close: function () {
          debug('Closing Subscriber')
          consumer.close(false, function () {})
        }
      }
    },
    createSubscriberGroup: async function (group, topic, messageHandler, fromOffset = 'latest') {
      debug('CreatingSubscribeGroup')
      var consumerGroup
      var messagequeue = []
      var subscriber = await new Promise((resolve, reject) => {
        var options = {
          autoCommit: true,
          id: 'consumer1',
          kafkaHost: kfnodes,
          // batch: undefined, // put client batch settings if you need them (see Client)
          groupId: group,
          sessionTimeout: 15000,
          protocol: ['roundrobin'],
          fromOffset: fromOffset
          // outOfRangeOffset: '
        }
        debug(`Creating ConsumerGroup for group ${group} and topic ${topic} from offset ${fromOffset}`)
        consumerGroup = new ConsumerGroup(options, topic)
        consumerGroup.on('error', onError)
        consumerGroup.on('message', onMessage)
        function onError (error) {
          console.error(error)
          console.error(error.stack)
        }
        consumerGroup.connect()
        consumerGroup.once('connect', () => {
          debug('Connected')
          resolve()
        })
        function onMessage (message) {
          messagequeue.push(message)
          if (messagequeue.length === 1) {
            dequeue()
          }
        }
        async function dequeue () {
          if (messagequeue.length > 0) {
            var message = messagequeue[0]
            if (message.key && message.value.length > 0) {
              debug(`Message on Topic=${message.topic} Partition=${message.partition} Offset=${message.offset} highWaterOffset=${message.highWaterOffse} Key=${message.key} value=${message.value}`)
              await messageHandler(JSON.parse(message.value))
            }
            messagequeue.shift()
            dequeue()
          }
        }
      })
      debug('CreatedSubscribeGroup')
      return {
        close: function () {
          debug('Closing Subscriber')
          consumerGroup.close(false, function () {
            debug('ConsumerGroup closed')
          })
        }
      }
    },
    retrieveBatchKeyValue: function (content, topic, start, length) {
      var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
      debug('Consuming from:', start, ' for length:', length)
      return new Promise(function (resolve, reject) {
        var options = {
          autoCommit: false,
          fetchMaxWaitMs: 1000,
          fetchMaxBytes: 1000000,
          fromOffset: true
        }
        var consumer = new Consumer(client, [{
          topic: topic,
          partition: 0,
          offset: start
        }], options)
        consumer.on('done', function (message) {
          consumer.close(true, function () {
            client.close()
            resolve(content)
          })
        })
        consumer.on('offsetOutOfRange', function (err) {
          debug(`Outset out of range ${err}`)
        })
        consumer.on('message', function (message) {
          if (message.key) {
            debug(`consumed msg from topic[${message.topic}] Partition[${message.partition}] Offset[${message.offset}] HW=${message.highWaterOffse} Key=${message.key} Value=>${message.value}`)
            content.data[message.key] = JSON.parse(message.value)
            content.offset = message.offset
          }
        })
      })
    },
    retrieveAllKeyValue: async function (groupid, topic) {
      var options = {
        id: 'consumer1',
        kafkaHost: kfnodes,
        groupId: groupid,
        sessionTimeout: 15000,
        protocol: ['roundrobin'],
        fetchMaxWaitMs: 1000,
        fetchMaxBytes: 1000000,
        fromOffset: 'earliest',
        commitOffsetsOnFirstJoin: true
      }
      var content = { data: {} }
      var offset = 0
      return new Promise(function (resolve, reject) {
        var consumerGroup = new ConsumerGroup(options, topic)
        consumerGroup.on('error', onError)
        consumerGroup.on('message', onMessage)
        consumerGroup.on('done', function (message) {
          debug(message)
          consumerGroup.close(true, function () {
            resolve(content)
          })
        })
        function onError (error) {
          console.error(error)
          console.error(error.stack)
        }
        function onMessage (message) {
          if (message.key && message.value.length > 0) {
            debug(`consumed msg from topic[${message.topic}] Partition[${message.partition}] Offset[${message.offset}] HW=${message.highWaterOffset} Key=${message.key} Value=>${message.value}`)
            content.data[message.key] = JSON.parse(message.value)
            content.offset = message.offset
          }
        }
      })
    },
    groupSelectAll: async function (groupid, topic) {
      var topicOffsets = await this.getOffset(topic)
      var latestOffset = topicOffsets[topic]['0'][0]
      var res = await this.retrieveAllKeyValue(groupid, topic)
      while (res.offset < (latestOffset - 1)) {
        await this.retrieveBatchKeyValue(res, topic, res.offset + 1, latestOffset - (res.offset + 1))
      }
      return res
    },
    selectAll: function (topic) {
      var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
      debug('Selecting all from topic:', topic)
      return new Promise(function (resolve, reject) {
        var content = []
        var options = {
          autoCommit: false,
          fetchMaxWaitMs: 1000,
          fetchMaxBytes: 10000,
          fromOffset: true
        }
        var consumer = new Consumer(client, [{
          topic: topic,
          partition: 0,
          offset: 0
        }], options)
        consumer.on('done', function (message) {
          consumer.close(true, function () {
            client.close()
            resolve(content)
          })
        })
        consumer.on('message', function (message) {
          if (message.key) {
            debug('consumed message offset:', message.offset, '=>', message.value)
            content.push(JSON.parse(message.value))
          }
        })
      })
    },
    calculateStartEnd: function (batchsize, offset, latestOffset, highwaterMark) {
      var start1 = latestOffset - batchsize - offset
      if (start1 < 0) { start1 = 0 }
      var end1 = start1 + batchsize > latestOffset ? latestOffset : start1 + batchsize
      var start2 = -1
      var end2 = -1
      if (start1 < highwaterMark && end1 > highwaterMark) {
        end2 = end1
        end1 = highwaterMark
        start2 = highwaterMark
      }
      return { start1, length1: end1 - start1, start2, length2: end2 - start2 }
    },
    retrieveBatch: function (topic, start, length) {
      var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
      debug('Consuming from:', start, ' for length:', length)
      return new Promise(function (resolve, reject) {
        var content = []
        var options = {
          autoCommit: false,
          fetchMaxWaitMs: 1000,
          fetchMaxBytes: 1000000,
          fromOffset: true
        }
        var consumer = new Consumer(client, [{
          topic: topic,
          partition: 0,
          offset: start
        }], options)
        consumer.on('done', function (message) {
          consumer.close(true, function () {
            client.close()
            resolve(content.slice(0, length))
          })
        })
        consumer.on('offsetOutOfRange', function (err) {
          debug(`Outset out of range ${err}`)
        })
        consumer.on('message', function (message) {
          if (message.key) {
            debug(`consumed msg from topic[${message.topic}] Partition[${message.partition}] Offset[${message.offset}] HW=${message.highWaterOffse} Key=${message.key} Value=>${message.value}`)
            content.push(JSON.parse(message.value))
          }
        })
      })
    },
    batchConsume: async function (groupid, topic, batchsize, offset = 0) {
      var topicOffsets = await this.getOffset(topic)
      if (!topicOffsets) { return null }
      var latestOffset = topicOffsets[topic]['0'][0]
      var highwaterMark = topicOffsets[topic]['0'][1]

      var { start1, length1, start2, length2 } = this.calculateStartEnd(batchsize, offset, latestOffset, highwaterMark)

      var content = await this.retrieveBatch(topic, start1, length1)
      if (start2 >= 0) {
        var content2 = await this.retrieveBatch(topic, start2, length2)
        content = content.concat(content2)
      }

      return content
    },
    getAdmin: function () {
      var client = new kafka.KafkaClient({ kafkaHost: kfnodes, autoConnect: true })
      const admin = new kafka.Admin(client)
      return {
        getGroups: async function () {
          return new Promise(function (resolve, reject) {
            admin.listGroups((err, res) => {
              if (err) {
                reject(err)
              } else {
                resolve(res)
              }
              client.close()
            })
          })
        }
      }
    }
  }
}

module.exports = K2Client
