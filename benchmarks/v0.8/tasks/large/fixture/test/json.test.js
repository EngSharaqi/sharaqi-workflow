import { test } from 'node:test';
import assert from 'node:assert/strict';
import { toJsonLines, parseJsonLines } from '../src/index.js';
import { ev } from './helpers.js';

test('round trip with data', () => {
  const events = [ev('file.read', 'bob', '2026-01-05T09:00:00Z', { data: { path: '/a' } })];
  assert.deepEqual(parseJsonLines(toJsonLines(events)), events);
});

test('line errors', () => {
  assert.throws(() => parseJsonLines('{nope\n'), /line 1/);
  assert.throws(() => parseJsonLines('{"id":"a","type":"login","at":"2026-01-05T09:00:00Z"}\n'), /line 1/);
});
