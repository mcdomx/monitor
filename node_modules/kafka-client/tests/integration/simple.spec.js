var { zookeeperclient, config } = require('../../index.js')
var consumerclient = zookeeperclient(config.zookeeperService)
var producerclient = zookeeperclient(config.zookeeperService)
var assert = require('assert')

var debug = require('debug')('kafka-client')

var uuid = require('uuid/v1')

describe('Given a zookeeper and kafka server running', () => {
	var result
	before(async () => {
		await consumerclient.connect(config.zookeeperService)
		await producerclient.connect(config.zookeeperService)
	})
	after(async () => {
		await consumerclient.disconnect()
		await producerclient.disconnect()
	})
	describe('When a topic is created', () => {
		var topic = 'testtopic' + uuid()
		before(async () => {
			await consumerclient.createTopic(topic)
		})
		it('Then topics contain the topic created', async function () {
			result = await consumerclient.getTopics()
			debug(result)
			assert.ok(result.indexOf(topic) > -1)
		})
	})

	describe('When a offset is requested', () => {
		var topic = 'testtopic' + uuid()
		before(async () => {
			await consumerclient.createTopic(topic)
		})
		it('Then offset for a new topic is 0', async function () {
			result = await consumerclient.getOffset(topic)
			debug(result)
			assert.ok(result)
		})
	})

	describe('When a consumer is consuming messages and a message is produced', () => {
		var topic = 'producertest'
		var key = 'key'
		var value = 'value1'

		var group = uuid()// a new group means we always read new messages which arrive

		var consumeMessage
		before(async () => {
			await consumerclient.createTopic(topic)
		})
		describe('When a single message is produced and read', () => {
			var result
			before(async () => {
				consumeMessage = await consumerclient.singleMessageConsumer(group, topic)
				await producerclient.produceTopicKeyValue(key, value, topic)
				result = await consumeMessage()
			})
			it('Then a message is received', async function () {
				assert.equal(result.key, key)
				assert.equal(result.value, value)
			})
			describe('When offsets are requested', () => {
				var offsets
				before(async () => {
					offsets = await consumerclient.getOffset(topic)
				})
				it('Then offset is 1', async function () {
					debug(offsets)
				})
			})
		})
	})

	describe('When a keyless message is produced', () => {
		var topic = 'producertestkeyless'
		var value = 'value1'

		var group = uuid()// a new group means we always read new messages which arrive

		var consumeMessage
		before(async () => {
			await consumerclient.createTopic(topic)
		})
		describe('When a single message is produced and read', () => {
			var result
			before(async () => {
				for (var i = 0; i < 5; i++) {
					await consumerclient.produceTopicValue(null, value, topic)
				}
			})
			describe('When offsets are requested', () => {
				var offsets
				before(async () => {
					offsets = await consumerclient.getOffset(topic)
				})
				it('Then offset is 1', async function () {
					debug(offsets)
				})
			})
		})
	})
})
