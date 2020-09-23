var { kafkaclient, config } = require('../../index.js')
var assert = require('assert')

var debug = require('debug')('kafka-client')

var kclient = kafkaclient()

var f = function () {
	this.property = '123'
}

var scenarios = {
	batchSize: [10,	20,		10,		10],
	offset: [0,		0,		5,		0],
	latestOffset: [100,	10,		20,		10],
	highwaterMark: [100,	10,		20,		5],
	start1: [90,	0,		5,		0],
	length1: [10,	10,		10,		5],
	start2: [-1,	-1,		-1,		5],
	length2: [0,		0,		0,		5]
}
for (var i = 0; i < scenarios.batchSize.length; i++) {
	describe(`Given batchsize=${scenarios.batchSize[i]},offset=${scenarios.offset[i]},latestOff=${scenarios.latestOffset[i]},highwaterMark=${scenarios.highwaterMark[i]}`, () => {
		var { start1, length1, start2, length2 } = kclient.calculateStartEnd(scenarios.batchSize[i], scenarios.offset[i], scenarios.latestOffset[i], scenarios.highwaterMark[i])
		var j = i
		it(`Then start1=${scenarios.start1[i]}`, function () {
			assert.equal(scenarios.start1[j], start1)
		})
		it(`Then length1=${scenarios.length1[i]}`, function () {
			assert.equal(scenarios.length1[j], length1)
		})
		it(`Then start2=${scenarios.start2[i]}`, function () {
			assert.equal(scenarios.start2[j], start2)
		})
		it(`Then length2=${scenarios.length2[i]}`, function () {
			assert.equal(scenarios.length2[j], length2)
		})
	})
}
