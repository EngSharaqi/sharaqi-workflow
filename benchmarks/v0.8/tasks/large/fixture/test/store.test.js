import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createStore, append, all, byUser, createEvent } from '../src/index.js';

const e = (id, userId, at) => createEvent({ id, type: 'login', userId, at });

test('orders by time then id', () => {
  const s = createStore();
  append(s, e('b', 'alice', '2026-01-05T10:00:00Z'));
  append(s, e('a', 'bob', '2026-01-05T10:00:00Z'));
  append(s, e('c', 'alice', '2026-01-04T10:00:00Z'));
  assert.deepEqual(all(s).map((x) => x.id), ['c', 'a', 'b']);
  assert.deepEqual(byUser(s, 'alice').map((x) => x.id), ['c', 'b']);
});

test('rejects duplicate ids', () => {
  const s = createStore();
  append(s, e('a', 'alice', '2026-01-05T10:00:00Z'));
  assert.throws(() => append(s, e('a', 'bob', '2026-01-05T11:00:00Z')), /duplicate/);
});
