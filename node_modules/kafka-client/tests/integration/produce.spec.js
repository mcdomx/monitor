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
	it('Then client is created', async function () {
		assert.ok(client)
	})
	describe('When a messages is produced', () => {
		var topic = 'testistic.testruns'
		var key = 'key'
		var value = 'value' // value is a string
		var offsets
		var initialOffset, latestOffset
		var produced
		before(async () => {
			produced = await client.produceTopicKeyValue(key, value, topic)
			offsets = await client.getOffset(topic)
			latestOffset = offsets[topic]['0'][0]
			initialOffset = offsets[topic]['0'][1]
			debug('Latest Offset', latestOffset)
			debug('Initial Offset', initialOffset)
		})
		it('Then the message is produced', () => {
			assert.ok(produced)
		})
	})
})
