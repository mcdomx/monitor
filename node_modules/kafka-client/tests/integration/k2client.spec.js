var { kafkaclient, config } = require('../../index.js')
var assert = require('assert')

var debug = require('debug')('kafka-client')

var uuid = require('uuid/v1')

describe('Given kafka server running', () => {
	let client = null
	var result
	before(async () => {
		client = kafkaclient(config.kafkaService)
	})
	after(function () {
	})
	it('Then client is created', async function () {
		assert.ok(client)
	})
	describe('When admin is created', () => {
		var admin
		before(async () => {
			admin = client.getAdmin()
		})
		it('Then admin is created', async function () {
			assert.ok(admin)
		})
		describe('When groups are requested', () => {
			var groups
			before(async () => {
				groups = await admin.getGroups()
			})
			it('Then groups are returned', async function () {
				debug(groups)
				assert.ok(groups)
			})
		})
	})
	describe('When a topics are requested repeatedly', () => {
		var result
		it('Then the topic is returned', async function () {
			result = await client.getTopics()
			debug(result)
			assert.ok(result)
		})
		it('Then the topic is returned again', async function () {
			result = await client.getTopics()
			debug(result)
			assert.ok(result)
		})
	})
	describe('When a topic is created', () => {
		var topic = 'testtopic' + uuid()
		before(async () => {
			await client.createTopic(topic)
		})
		it('Then topics contain the topic created', async function () {
			result = await client.getTopics()
			debug(result)
			assert.ok(result.indexOf(topic) > -1)
		})
	})
	describe('When a offset is requested', () => {
		var topic = 'testtopic' + uuid()
		before(async () => {
			await client.createTopic(topic)
		})
		it('Then offset for a new topic is 0', async function () {
			result = await client.getOffset(topic)
			debug(result)
			assert.ok(result)
		})
	})
	describe('When request messages from a non-existent topic', () => {
		var result
		var group = 'user@example.com'
		before(async () => {
			result = await client.batchConsume(group, `testtopic.${uuid()}`, 1)
		})
		it('Then null is returned', async function () {
			assert.equal(null, result)
		})
	})
	describe('When multiple messages are produced', () => {
		var topic = 'test.topic'
		var key = 'key'
		var value = 'value' // value is a string
		var group = 'user@example.com'// groups can be users who are accessing the data
		var offsets
		var consumeMessage
		var initialOffset, latestOffset
		var batchsize = 5
		var produced
		before(async () => {
			await client.createTopic(topic)
			for (var i = 0; i < batchsize; i++) {
				produced = await client.produceTopicKeyValue(key, value + i, topic)
			}
			offsets = await client.getOffset(topic)
			latestOffset = offsets[topic]['0'][0]
			initialOffset = offsets[topic]['0'][1]
			debug('Latest Offset', latestOffset)
			debug('Initial Offset', initialOffset)
		})
		describe('When a batch of messages is read', () => {
			var result
			before(async () => {
				consumeMessage = await client.batchConsume(group, topic, batchsize, 5)
				consumeMessage = await client.batchConsume(group, topic, batchsize, 10)
			})
			it('Then a batch is received', async function () {
				assert.ok(consumeMessage.length === batchsize)
				debug(consumeMessage)
			})
		})
	})
	// describe.skip('When request messages from ', () => {
	// 	var result
	// 	var group = 'consumer1'
	// 	before(async () => {
	// 		result = await client.batchConsume(group, `testistic.statistics.all.all`, 5,22)
	// 	})
	// 	it('Then null is returned', async function () {
	// 		assert.equal(result.length,5)
	// 	})
	// })
})
