import { parseTimestamp } from './util.js';

// One user's events in time order as "HH:MM type" lines (UTC).
export function timeline(events, userId) {
  return events
    .filter((e) => e.userId === userId)
    .sort((a, b) => parseTimestamp(a.at) - parseTimestamp(b.at))
    .map((e) => `${e.at.slice(11, 16)} ${e.type}`);
}

// Splits each user's events into sessions: a gap longer than gapMinutes starts a new one.
// Returns [{ userId, start, end, count }] ordered by start, then userId.
export function sessions(events, gapMinutes = 30) {
  if (!Number.isFinite(gapMinutes) || gapMinutes <= 0) throw new RangeError('gapMinutes must be positive');
  const gap = gapMinutes * 60000;
  const byUser = new Map();
  for (const e of [...events].sort((a, b) => parseTimestamp(a.at) - parseTimestamp(b.at))) {
    if (!byUser.has(e.userId)) byUser.set(e.userId, []);
    byUser.get(e.userId).push(e);
  }
  const out = [];
  for (const [userId, list] of byUser) {
    let cur = null;
    for (const e of list) {
      const t = parseTimestamp(e.at);
      if (cur && t - parseTimestamp(cur.end) <= gap) {
        cur.end = e.at;
        cur.count++;
      } else {
        cur = { userId, start: e.at, end: e.at, count: 1 };
        out.push(cur);
      }
    }
  }
  return out.sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : a.userId < b.userId ? -1 : 1));
}
