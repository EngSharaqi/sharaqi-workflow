import { parseTimestamp } from './util.js';

// from is inclusive, to is exclusive.
export function filterEvents(events, { type, typePrefix, userId, from, to } = {}) {
  const fromMs = from === undefined ? -Infinity : parseTimestamp(from);
  const toMs = to === undefined ? Infinity : parseTimestamp(to);
  return events.filter((e) => {
    if (type !== undefined && e.type !== type) return false;
    if (typePrefix !== undefined && !(e.type === typePrefix || e.type.startsWith(typePrefix + '.'))) return false;
    if (userId !== undefined && e.userId !== userId) return false;
    const t = parseTimestamp(e.at);
    return t >= fromMs && t < toMs;
  });
}
