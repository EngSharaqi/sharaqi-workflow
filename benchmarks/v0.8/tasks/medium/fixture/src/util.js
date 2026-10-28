// Calendar days as 'YYYY-MM-DD' strings, computed in UTC so time zones never shift a day.
const DAY_MS = 86400000;
const DAY_RE = /^\d{4}-\d{2}-\d{2}$/;

export function parseDay(text) {
  if (typeof text !== 'string' || !DAY_RE.test(text)) {
    throw new Error(`invalid day: ${text} (expected YYYY-MM-DD)`);
  }
  const d = new Date(text + 'T00:00:00Z');
  if (Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== text) {
    throw new Error(`invalid day: ${text}`);
  }
  return d;
}

export function dayKey(date) {
  return date.toISOString().slice(0, 10);
}

export function addDays(day, n) {
  return dayKey(new Date(parseDay(day).getTime() + n * DAY_MS));
}

export function daysBetween(from, to) {
  return Math.round((parseDay(to) - parseDay(from)) / DAY_MS);
}
