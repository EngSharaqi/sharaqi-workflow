import { parseTimestamp, isNonEmptyString } from './util.js';

const TYPE_RE = /^[a-z]+(\.[a-z]+)*$/;

// An audit event: who (userId) did what (type) when (at), with optional data.
export function createEvent({ id, type, userId, at, data = {} } = {}) {
  if (!isNonEmptyString(id)) throw new Error('event id is required');
  if (typeof type !== 'string' || !TYPE_RE.test(type)) {
    throw new Error(`invalid event type: ${type} (expected dotted lower-case words)`);
  }
  if (!isNonEmptyString(userId)) throw new Error('event userId is required');
  parseTimestamp(at);
  if (data === null || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('event data must be an object');
  }
  return { id, type, userId, at, data };
}
