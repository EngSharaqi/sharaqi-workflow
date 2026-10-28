import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHabit, currentStreak, longestStreak } from '../src/index.js';

const read = createHabit({ name: 'Read', createdOn: '2026-01-01' });
const days = ['2026-01-02', '2026-01-03', '2026-01-05', '2026-01-06', '2026-01-07'];

test('current streak ending today', () => {
  assert.equal(currentStreak(read, days, '2026-01-07'), 3);
});

test('current streak ending yesterday', () => {
  assert.equal(currentStreak(read, days, '2026-01-08'), 3);
});

test('broken streak', () => {
  assert.equal(currentStreak(read, days, '2026-01-09'), 0);
});

test('longest streak', () => {
  assert.equal(longestStreak(read, days), 3);
  assert.equal(longestStreak(read, []), 0);
});
