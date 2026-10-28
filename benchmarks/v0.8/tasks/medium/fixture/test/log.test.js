import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHabit, createLog, checkIn, checkinsFor } from '../src/index.js';

const read = createHabit({ name: 'Read', createdOn: '2026-01-05' });

test('records sorted unique days', () => {
  const log = createLog();
  checkIn(log, read, '2026-01-07');
  checkIn(log, read, '2026-01-06');
  checkIn(log, read, '2026-01-07');
  assert.deepEqual(checkinsFor(log, read), ['2026-01-06', '2026-01-07']);
});

test('rejects a day before the habit existed', () => {
  assert.throws(() => checkIn(createLog(), read, '2026-01-04'));
});
