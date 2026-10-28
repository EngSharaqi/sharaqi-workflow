import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHabit, completionRate } from '../src/index.js';

const read = createHabit({ name: 'Read', createdOn: '2026-01-03' });

test('rate from the creation day', () => {
  assert.equal(completionRate(read, ['2026-01-03', '2026-01-04'], '2026-01-01', '2026-01-06'), 0.5);
});

test('empty range', () => {
  assert.equal(completionRate(read, [], '2026-01-05', '2026-01-04'), null);
});
