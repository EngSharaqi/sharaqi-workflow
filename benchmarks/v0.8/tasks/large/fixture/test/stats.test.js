import { test } from 'node:test';
import assert from 'node:assert/strict';
import { eventsPerUser, busiestDay } from '../src/index.js';
import { ev } from './helpers.js';

test('events per user', () => {
  assert.equal(eventsPerUser([ev('a', 'u1', '2026-01-05T09:00:00Z'), ev('a', 'u1', '2026-01-05T10:00:00Z'), ev('a', 'u2', '2026-01-05T11:00:00Z')]), 1.5);
  assert.equal(eventsPerUser([]), null);
});

test('busiest day, earliest on a tie', () => {
  assert.equal(busiestDay([ev('a', 'u', '2026-01-06T09:00:00Z'), ev('a', 'u', '2026-01-05T09:00:00Z')]), '2026-01-05');
  assert.equal(busiestDay([]), null);
});
