import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHabit } from '../src/index.js';

test('creates a habit', () => {
  assert.deepEqual(createHabit({ name: ' Read ', createdOn: '2026-01-05' }), { name: 'Read', createdOn: '2026-01-05' });
});

test('validates name and day', () => {
  assert.throws(() => createHabit({ name: '', createdOn: '2026-01-05' }));
  assert.throws(() => createHabit({ name: 'x'.repeat(61), createdOn: '2026-01-05' }));
  assert.throws(() => createHabit({ name: 'Read', createdOn: '2026-02-30' }));
});
