import { dayOf } from './util.js';

const KEYS = {
  type: (e) => e.type,
  userId: (e) => e.userId,
  day: (e) => dayOf(e.at),
};

// { <key value>: count }, keys in first-seen order.
export function countBy(events, key) {
  const get = KEYS[key];
  if (!get) throw new Error(`unknown group key: ${key}`);
  const out = {};
  for (const e of events) {
    const k = get(e);
    out[k] = (out[k] || 0) + 1;
  }
  return out;
}
