var { zookeeperclient, config } = require('../../index.js')
var consumerclient = zookeeperclient(config.zookeeperService)
var producerclient = zookeeperclient(config.zookeeperService)
var assert = require('assert')

var debug = require('debug')('kafka-consumerclient')

var uuid = require('uuid/v1')

var topic = 'testinstances'
var key = 'key'
var value = 'value' // value is a string

// var group = uuid();//a new group id each time means we always read new messages which arrive
var group = 'user@example.com'// groups can be users who are accessing the data

describe('Given a zookeeper and kafka server running', () => {
	var result
	before(async () => {
		await consumerclient.connect()
		await producerclient.connect()
	})
	after(async () => {
		await consumerclient.disconnect()
		await producerclient.disconnect()
	})

	describe('When multiple messages are produced', () => {
		var offsets
		var consumeMessage
		var initialOffset, latestOffset
		var batchsize = 5
		var produced
		before(async () => {
			await consumerclient.createTopic(topic)
			for (var i = 0; i < batchsize; i++) {
				produced = await producerclient.produceTopicKeyValue(key, value + i, topic)
			}
			offsets = await consumerclient.getOffset(topic)
			latestOffset = offsets[topic]['0'][0]
			initialOffset = offsets[topic]['0'][1]
			debug('Latest Offset', latestOffset)
			debug('Initial Offset', initialOffset)
		})
		describe('When a batch of messages is read', () => {
			var result
			before(async () => {
				consumeMessage = await consumerclient.batchConsume(group, topic, batchsize)
			})
			it('Then a batch is received', async function () {
				assert.ok(consumeMessage.length === batchsize)
				debug(consumeMessage)
			})
		})
	})
})
