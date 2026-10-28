// Hidden tests for the medium task: only behaviour task.txt states.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as lib from '../src/index.js';

const weekly = (createdOn = '2026-01-01') => lib.createHabit({ name: 'Run', createdOn, frequency: 'weekly' });
const daily = () => lib.createHabit({ name: 'Read', createdOn: '2026-01-01' });

test('H1 frequency defaults to daily', () => assert.equal(daily().frequency, 'daily'));
test('H2 weekly is stored', () => assert.equal(weekly().frequency, 'weekly'));
test('H3 other frequencies throw', () => {
  assert.throws(() => lib.createHabit({ name: 'Run', createdOn: '2026-01-01', frequency: 'monthly' }));
});
// 2026-01-05 is a Monday. Weeks: W2 = 01-05..01-11, W3 = 01-12..01-18, W4 = 01-19..01-25.
test('H4 weekly current streak ending this week', () => {
  const days = ['2026-01-05', '2026-01-14', '2026-01-18', '2026-01-19'];
  assert.equal(lib.currentStreak(weekly(), days, '2026-01-21'), 3);
});
test('H5 weekly current streak ending last week', () => {
  assert.equal(lib.currentStreak(weekly(), ['2026-01-05', '2026-01-14'], '2026-01-21'), 2);
});
test('H6 weekly streak broken', () => {
  assert.equal(lib.currentStreak(weekly(), ['2026-01-05', '2026-01-14'], '2026-01-28'), 0);
});
test('H7 weekly longest streak', () => {
  assert.equal(lib.longestStreak(weekly(), ['2026-01-05', '2026-01-12', '2026-01-26']), 2);
});
// 2026-01-01 is a Thursday; the range 01-01..01-31 touches 5 ISO weeks.
test('H8 weekly completion rate', () => {
  assert.equal(lib.completionRate(weekly(), ['2026-01-02', '2026-01-06', '2026-01-07'], '2026-01-01', '2026-01-31'), 0.4);
});
test('H9 daily unchanged', () => {
  const days = ['2026-01-02', '2026-01-03', '2026-01-05', '2026-01-06', '2026-01-07'];
  assert.equal(lib.currentStreak(daily(), days, '2026-01-08'), 3);
  assert.equal(lib.longestStreak(daily(), days), 3);
  assert.equal(lib.completionRate(daily(), ['2026-01-01', '2026-01-02'], '2026-01-01', '2026-01-04'), 0.5);
});
test('H10 CSV round trip with frequency', () => {
  const habits = [weekly(), daily()];
  assert.equal(lib.CSV_HEADER, 'name,createdOn,frequency');
  assert.deepEqual(lib.parseCsv(lib.toCsv(habits)), habits);
});
test('H11 CSV empty frequency cell is daily', () => {
  assert.equal(lib.parseCsv('name,createdOn,frequency\nRead,2026-01-01,\n')[0].frequency, 'daily');
});
test('H12 weekly format', () => {
  assert.equal(lib.formatHabit(weekly(), 2), 'Run — streak 2 weeks');
  assert.equal(lib.formatHabit(weekly(), 1), 'Run — streak 1 week');
  assert.equal(lib.formatHabit(daily(), 2), 'Read — streak 2 days');
});
test('H13 filter by frequency', () => {
  assert.deepEqual(lib.filterHabits([weekly(), daily()], { frequency: 'weekly' }).map((h) => h.name), ['Run']);
});
