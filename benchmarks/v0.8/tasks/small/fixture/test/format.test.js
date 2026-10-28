import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatDuration } from '../src/index.js';

test('formats hours and minutes', () => {
  assert.equal(formatDuration(5400), '1h 30m');
  assert.equal(formatDuration(7200), '2h');
});

test('zero', () => {
  assert.equal(formatDuration(0), '0m');
});

test('rejects negatives', () => {
  assert.throws(() => formatDuration(-1), RangeError);
});
