// Hidden tests for the small task: only behaviour task.txt states.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseDuration, formatDuration } from '../src/index.js';

test('H1 seconds', () => assert.equal(parseDuration('90s'), 90));
test('H2 days', () => assert.equal(parseDuration('2d'), 172800));
test('H3 all units', () => assert.equal(parseDuration('1d2h3m4s'), 93784));
test('H4 old forms unchanged', () => {
  assert.equal(parseDuration('1h30m'), 5400);
  assert.equal(parseDuration('45m'), 2700);
});
test('H5 repeated unit throws', () => assert.throws(() => parseDuration('1h1h')));
test('H6 out of order throws', () => {
  assert.throws(() => parseDuration('30m1h'));
  assert.throws(() => parseDuration('1s1m'));
});
test('H7 format all units', () => assert.equal(formatDuration(93784), '1d 2h 3m 4s'));
test('H8 format days only', () => assert.equal(formatDuration(86400), '1d'));
test('H9 format seconds only', () => assert.equal(formatDuration(59), '59s'));
test('H10 format zero unchanged', () => assert.equal(formatDuration(0), '0m'));
