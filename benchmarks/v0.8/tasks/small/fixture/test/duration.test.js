import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseDuration } from '../src/index.js';

test('hours and minutes', () => {
  assert.equal(parseDuration('1h30m'), 5400);
  assert.equal(parseDuration('45m'), 2700);
  assert.equal(parseDuration('2h'), 7200);
});

test('surrounding spaces are ignored', () => {
  assert.equal(parseDuration(' 5m '), 300);
});

test('rejects garbage', () => {
  assert.throws(() => parseDuration('soon'));
  assert.throws(() => parseDuration(''));
  assert.throws(() => parseDuration(5), TypeError);
});
