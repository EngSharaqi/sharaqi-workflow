import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatEvent, formatEvents } from '../src/index.js';
import { ev } from './helpers.js';

test('one line per event', () => {
  const a = ev('user.login', 'alice', '2026-01-05T09:00:00Z');
  assert.equal(formatEvent(a), '2026-01-05T09:00:00Z user=alice user.login');
  assert.equal(formatEvents([a, a]).split('\n').length, 2);
});
