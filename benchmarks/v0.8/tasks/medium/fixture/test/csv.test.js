import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHabit, toCsv, parseCsv } from '../src/index.js';

test('round trip with quoting', () => {
  const habits = [createHabit({ name: 'Read, then write', createdOn: '2026-01-01' })];
  assert.deepEqual(parseCsv(toCsv(habits)), habits);
});

test('bad rows name their line', () => {
  assert.throws(() => parseCsv('name,createdOn\nRead,2026-13-01\n'), /row 2/);
});
