import { parseTimestamp, DAY_MS } from './util.js';

// Drops events older than maxAgeDays at `now`. An event exactly maxAgeDays old is kept.
export function applyRetention(events, now, { maxAgeDays = 30 } = {}) {
  if (!Number.isInteger(maxAgeDays) || maxAgeDays < 1) throw new RangeError('maxAgeDays must be a positive integer');
  const nowMs = parseTimestamp(now);
  return events.filter((e) => nowMs - parseTimestamp(e.at) <= maxAgeDays * DAY_MS);
}
