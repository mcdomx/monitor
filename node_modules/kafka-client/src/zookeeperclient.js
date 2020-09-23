// This client implementation connects Zookeeper
// This is understood to be an older style interface

var kafka = require('kafka-node')
var ConsumerGroup = kafka.ConsumerGroup
var HighLevelProducer = kafka.HighLevelProducer
var Client = kafka.Client

var Consumer = kafka.Consumer

var debug = require('debug')('kafka-client')

const KClient = function (zookeeper) {
  var zk = zookeeper
  var client = null
  return {
    connect: async function () {
        client = new Client(zk)
        await new Promise(function (resolve, reject) {
          client.once('connect', function () {
            debug('connected')
            // res();
          })
          client.once('ready', function () {
            debug('ready')
            resolve()
          })
          client.on('error', function (error) {
            reject(error)
          })
      })
    },
    disconnect: function () {
      client.close(function () {
        debug('disconnected')
      })
    },
    createTopic: function (topic) {
      return new Promise(function (resolve, reject) {
        client.createTopics(topic, function (error, results) {
          if (error) {
            reject(error)
          } else {
            debug('CreatedTopic:' + results)
            resolve(results)
          }
        })
      })
    },
    getTopics: async function () {
       var result = await new Promise(function (resolve, reject) {
        client.loadMetadataForTopics([], function (error, results) {
        if (error) {
          console.log(error)
            reject(error)
        } else {
            resolve(results)
          }
        })
      })
      return result.map(function (node) {
        return node['metadata'] ? Object.keys(node.metadata) : []
      }).reduce((a, b) => a.concat(b), [])
    },
    producePayload: function (payload) {
      return new Promise(function (resolve, reject) {
        var producer = new HighLevelProducer(client)
            producer.send(payload, function (error, result) {
              debug('Sent payload to Kafka: ', payload)
              if (error) {
                console.error(error)
                reject(error)
              } else {
                resolve(true)
              }
            })
          })
    },

    produceTopicValue: function (value, topic) {
      var payload = [{
        key: null,
        topic: topic,
        messages: [value],
        attributes: 0 /* Use GZip compression for the payload */
      }]
      return this.producePayload(payload)
    },
    produceTopicKeyValue: function (key, value, topic) {
      var payload = [{
        key: key,
        topic: topic,
        messages: [value],
        attributes: 0 /* Use GZip compression for the payload */
      }]
      return this.producePayload(payload)
    },
    getOffset: function (topic) {
      return new Promise(function (resolve, reject) {
        var offset = new kafka.Offset(client)
        offset.fetch([
          {
            topic,
            time: -1, // not sure why this gives us the latest offsets
            maxNum: 10
          }
          // {
          //   topic: "producertest",
          //   time: -1,//not sure why this gives us the latest offsets
          //   maxNum: 10
          // },
        ], function (err, data) {
          if (err) {
            reject(err)
          } else if (data) {
            resolve(data)
          }
        })
        // offset.fetchLatestOffsets([topic],function(err,data){
        //   if(err){
        //     rej(err)
        //   } else if(data){
        //     res(data)
        //   }
        // })
      })
    },
    singleMessageConsumer: function (groupid, topic) {
      return new Promise(function (resolve, reject) {
        var topics = [ topic ]
        var consumerOptions = {
          host: zookeeper,
          autoCommit: true,
          groupId: groupid,
          sessionTimeout: 10000,
          protocol: ['roundrobin'],
          commitOffsetOnFirstJoin: true,
          fromOffset: 'latest' // equivalent of auto.offset.reset valid values are 'none', 'latest', 'earliest'
        }
        var consumerGroup = new ConsumerGroup(Object.assign({ id: 'consumer1' }, consumerOptions), topics)

          var consumeFn = function (groupid, topic) {
            return new Promise(function (resolve, reject) {
              consumerGroup.once('message', function (message) {
                debug('consumed message')
                debug(message)
                consumerGroup.close(true, function () {
                  resolve(message)
                })
              })
              consumerGroup.on('error', function (err) {
                console.error(err)
                reject(err)
              })
            })
          }
          consumerGroup.on('connect', function (message) {
            debug('connect')
            resolve(consumeFn)
          })

          return consumeFn
      })
    },
    batchConsume: async function (groupid, topic, batchsize) {
      var topicOffsets = await this.getOffset(topic)
      var latestOffset = topicOffsets[topic]['0'][0]
      var targetOffset = latestOffset - batchsize > 0 ? latestOffset - batchsize : 0

      return new Promise(function (resolve, reject) {
        var content = []
        var options = {
          autoCommit: false,
          fetchMaxWaitMs: 1000,
          fetchMaxBytes: 1024,
          fromOffset: true
        }
        var consumer = new Consumer(client, [{
          topic: topic,
          partition: 0,
          offset: targetOffset
        }], options)
        consumer.on('done', function (message) {
          consumer.close(true, function () {
            resolve(content)
          })
        })
        consumer.on('message', function (message) {
          if (message.key) {
            debug('consumed message offset:', message.offset, '=>', message.value)
            content.push(message.value)
          }
        })
      })
    }
  }
}

module.exports = KClient
