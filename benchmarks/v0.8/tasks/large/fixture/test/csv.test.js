import { test } from 'node:test';
import assert from 'node:assert/strict';
import { toCsv, parseCsv, CSV_HEADER } from '../src/index.js';
import { ev } from './helpers.js';

test('round trip without data', () => {
  const events = [ev('user.login', 'alice, jr', '2026-01-05T09:00:00Z')];
  assert.deepEqual(parseCsv(toCsv(events)), events);
});

test('header and row errors', () => {
  assert.equal(CSV_HEADER, 'id,type,userId,at');
  assert.throws(() => parseCsv('id,type\n'), /header/);
  assert.throws(() => parseCsv(`${CSV_HEADER}\na,login,alice,yesterday\n`), /row 2/);
});
