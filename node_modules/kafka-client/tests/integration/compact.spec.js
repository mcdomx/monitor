var { kafkaclient, config } = require('../../index.js')
var assert = require('assert')

var debug = require('debug')('kafka-client')

var topic = 'integrationtest.compact'
var group = 'user_example.com'// groups can be users who are accessing the data

describe('Given kafka server running', () => {
	let consumerclient = null
	var result
	before(async () => {
		consumerclient = kafkaclient(config.kafkaService)
	})
	it('Then client is created', async function () {
		assert.ok(consumerclient)
	})
	describe('When a offset is requested', () => {
		before(async () => {
			await consumerclient.createTopic(topic)
		})
		it('Then offset for a new topic is 0', async function () {
			result = await consumerclient.getOffset(topic)
			debug(result)
			assert.ok(result)
		})
	})
	describe('When multiple messages are produced to a compact topic', () => {
		var topic = 'test.topic.compact'
		var key = 'key'
		var rand = Math.floor((Math.random() * 100) + 1)
		var value = `value-${rand}-` // value is a string
		var group = 'user.example.com'// groups can be users who are accessing the data
		var offsets
		var consumeMessage
		var initialOffset, latestOffset
		var createBatchSize = 10
		var produced

		before(async () => {
			await consumerclient.createTopic(topic)
			for (var i = 0; i < createBatchSize; i++) {
				var k = key + (i % 3)
				produced = await consumerclient.produceTopicKeyValue(k, value + i, topic)
			}
			offsets = await consumerclient.getOffset(topic)
			debug(offsets)
		})
		describe('When messages are read', () => {
			var result
			before(async () => {
				// consumeMessage = await client.batchConsume(group, topic, readBatchSize,0)
				consumeMessage = await consumerclient.groupSelectAll(group, topic)
			})
			it('Then the latest set of values is returned', async function () {
				debug(consumeMessage)
				assert.ok(Object.keys(consumeMessage.data).length === 3)
				assert.ok(consumeMessage.data.key0.startsWith(value))
				assert.ok(consumeMessage.data.key1.startsWith(value))
				assert.ok(consumeMessage.data.key2.startsWith(value))
			})
		})
	})
})
