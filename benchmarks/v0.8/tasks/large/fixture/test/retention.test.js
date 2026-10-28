import { test } from 'node:test';
import assert from 'node:assert/strict';
import { applyRetention } from '../src/index.js';
import { ev } from './helpers.js';

const now = '2026-02-01T00:00:00Z';

test('keeps events up to maxAgeDays old', () => {
  const events = [ev('a', 'u', '2026-01-02T00:00:00Z'), ev('a', 'u', '2026-01-01T23:59:59Z')];
  assert.equal(applyRetention(events, now).length, 1);
  assert.equal(applyRetention(events, now, { maxAgeDays: 31 }).length, 2);
  assert.throws(() => applyRetention(events, now, { maxAgeDays: 0 }), RangeError);
});
