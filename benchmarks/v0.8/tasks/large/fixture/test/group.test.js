import { test } from 'node:test';
import assert from 'node:assert/strict';
import { countBy } from '../src/index.js';
import { ev } from './helpers.js';

const events = [
  ev('login', 'alice', '2026-01-05T09:00:00Z'),
  ev('login', 'bob', '2026-01-05T10:00:00Z'),
  ev('logout', 'alice', '2026-01-06T09:00:00Z'),
];

test('counts by type, user and day', () => {
  assert.deepEqual(countBy(events, 'type'), { login: 2, logout: 1 });
  assert.deepEqual(countBy(events, 'userId'), { alice: 2, bob: 1 });
  assert.deepEqual(countBy(events, 'day'), { '2026-01-05': 2, '2026-01-06': 1 });
  assert.throws(() => countBy(events, 'size'));
});
