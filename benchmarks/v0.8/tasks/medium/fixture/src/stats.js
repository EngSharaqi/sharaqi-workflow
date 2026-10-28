import { addDays, daysBetween } from './util.js';

// Share of days from max(from, createdOn) to `to` (inclusive) with a check-in, rounded to two
// decimals. null when that range is empty.
export function completionRate(habit, days, from, to) {
  const start = from > habit.createdOn ? from : habit.createdOn;
  if (start > to) return null;
  const total = daysBetween(start, to) + 1;
  const set = new Set(days);
  let hit = 0;
  for (let day = start; day <= to; day = addDays(day, 1)) {
    if (set.has(day)) hit++;
  }
  return Math.round((hit / total) * 100) / 100;
}
