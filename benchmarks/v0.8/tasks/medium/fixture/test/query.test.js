import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHabit, filterHabits, sortHabits, formatHabit } from '../src/index.js';

const habits = [
  createHabit({ name: 'Run', createdOn: '2026-02-01' }),
  createHabit({ name: 'Read', createdOn: '2026-01-01' }),
];

test('filters by name and date', () => {
  assert.deepEqual(filterHabits(habits, { nameContains: 'RE' }).map((h) => h.name), ['Read']);
  assert.deepEqual(filterHabits(habits, { createdAfter: '2026-01-15' }).map((h) => h.name), ['Run']);
});

test('sorts', () => {
  assert.deepEqual(sortHabits(habits).map((h) => h.name), ['Read', 'Run']);
  assert.deepEqual(sortHabits(habits, 'createdOn', 'desc').map((h) => h.name), ['Run', 'Read']);
  assert.throws(() => sortHabits(habits, 'size'));
});

test('formats', () => {
  assert.equal(formatHabit(habits[1], 1), 'Read — streak 1 day');
  assert.equal(formatHabit(habits[1], 4), 'Read — streak 4 days');
});
