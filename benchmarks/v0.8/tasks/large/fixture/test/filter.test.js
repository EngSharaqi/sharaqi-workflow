import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filterEvents } from '../src/index.js';
import { ev } from './helpers.js';

const events = [
  ev('user.login', 'alice', '2026-01-05T09:00:00Z'),
  ev('user.logout', 'alice', '2026-01-05T17:00:00Z'),
  ev('file.read', 'bob', '2026-01-06T09:00:00Z'),
];

test('by type, prefix and user', () => {
  assert.equal(filterEvents(events, { type: 'file.read' }).length, 1);
  assert.equal(filterEvents(events, { typePrefix: 'user' }).length, 2);
  assert.equal(filterEvents(events, { userId: 'bob' }).length, 1);
});

test('time range is half open', () => {
  assert.equal(filterEvents(events, { from: '2026-01-05T17:00:00Z', to: '2026-01-06T09:00:00Z' }).length, 1);
});
