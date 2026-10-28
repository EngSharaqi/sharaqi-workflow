import { test } from 'node:test';
import assert from 'node:assert/strict';
import { timeline, sessions } from '../src/index.js';
import { ev } from './helpers.js';

const events = [
  ev('logout', 'alice', '2026-01-05T09:40:00Z'),
  ev('login', 'alice', '2026-01-05T09:00:00Z'),
  ev('login', 'bob', '2026-01-05T09:10:00Z'),
  ev('login', 'alice', '2026-01-05T11:00:00Z'),
];

test('timeline of one user', () => {
  assert.deepEqual(timeline(events, 'alice'), ['09:00 login', '09:40 logout', '11:00 login']);
});

test('sessions split on gaps', () => {
  assert.deepEqual(sessions(events, 60).map((s) => [s.userId, s.count]), [['alice', 2], ['bob', 1], ['alice', 1]]);
  assert.throws(() => sessions(events, 0), RangeError);
});
