// Timestamps are ISO 8601 in UTC with a Z suffix: 2026-01-05T10:00:00Z (milliseconds optional).
const TS_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;
export const DAY_MS = 86400000;

export function parseTimestamp(text) {
  if (typeof text !== 'string' || !TS_RE.test(text) || Number.isNaN(Date.parse(text))) {
    throw new Error(`invalid timestamp: ${text}`);
  }
  return Date.parse(text);
}

export function isNonEmptyString(v) {
  return typeof v === 'string' && v.trim() !== '';
}

export function dayOf(at) {
  return at.slice(0, 10);
}
