import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createEvent } from '../src/index.js';

test('creates an event with default data', () => {
  assert.deepEqual(createEvent({ id: 'a', type: 'user.login', userId: 'alice', at: '2026-01-05T10:00:00Z' }),
    { id: 'a', type: 'user.login', userId: 'alice', at: '2026-01-05T10:00:00Z', data: {} });
});

test('validates every field', () => {
  const ok = { id: 'a', type: 'login', userId: 'alice', at: '2026-01-05T10:00:00Z' };
  assert.throws(() => createEvent({ ...ok, id: '' }), /id/);
  assert.throws(() => createEvent({ ...ok, type: 'Login' }), /type/);
  assert.throws(() => createEvent({ ...ok, userId: ' ' }), /userId/);
  assert.throws(() => createEvent({ ...ok, at: '2026-01-05 10:00' }), /timestamp/);
  assert.throws(() => createEvent({ ...ok, data: [] }), /data/);
});
