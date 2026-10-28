import { parseDay } from './util.js';

// A log keeps each habit's check-in days. One check-in per day; repeats are ignored.
export function createLog() {
  return { days: new Map() };
}

export function checkIn(log, habit, day) {
  parseDay(day);
  if (day < habit.createdOn) throw new Error(`${day} is before ${habit.name} was created`);
  if (!log.days.has(habit.name)) log.days.set(habit.name, new Set());
  log.days.get(habit.name).add(day);
}

export function checkinsFor(log, habit) {
  return [...(log.days.get(habit.name) || [])].sort();
}
