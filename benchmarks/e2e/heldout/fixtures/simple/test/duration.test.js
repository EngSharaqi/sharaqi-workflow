import assert from 'node:assert/strict';
import { test } from 'node:test';

import { formatDuration } from '../src/duration.js';

test('formats whole units', () => {
    assert.equal(formatDuration(0), '0s');
    assert.equal(formatDuration(1000), '1s');
    assert.equal(formatDuration(61000), '1m 1s');
    assert.equal(formatDuration(3600000), '1h 0m 0s');
    assert.equal(formatDuration(3723000), '1h 2m 3s');
});

test('rejects bad input', () => {
    assert.throws(() => formatDuration(-1), RangeError);
    assert.throws(() => formatDuration(NaN), RangeError);
});
