import assert from 'node:assert/strict';
import { test } from 'node:test';

import { formatDuration } from '../src/duration.js';
import { jobLine } from '../src/log.js';

test('hidden: the reported case', () => assert.equal(formatDuration(119999), '2m 0s'));
test('hidden: just under a minute rounds up to 1m 0s', () => assert.equal(formatDuration(59500), '1m 0s'));
test('hidden: just under an hour rounds up to 1h 0m 0s', () => assert.equal(formatDuration(3599999), '1h 0m 0s'));
test('hidden: just under a day', () => assert.equal(formatDuration(86399600), '24h 0m 0s'));
test('hidden: half a second rounds up', () => assert.equal(formatDuration(500), '1s'));
test('hidden: under half a second is 0s', () => assert.equal(formatDuration(499), '0s'));
test('hidden: 1.4 s rounds down', () => assert.equal(formatDuration(61400), '1m 1s'));
test('hidden: existing format kept', () => {
    assert.equal(formatDuration(3723000), '1h 2m 3s');
    assert.equal(formatDuration(3600000), '1h 0m 0s');
    assert.equal(formatDuration(45000), '45s');
});
test('hidden: bad input still throws RangeError', () => {
    assert.throws(() => formatDuration(-1), RangeError);
    assert.throws(() => formatDuration(Infinity), RangeError);
});
test('hidden: log line uses it', () => assert.equal(jobLine('build', 1000, 120999), 'build finished in 2m 0s'));
