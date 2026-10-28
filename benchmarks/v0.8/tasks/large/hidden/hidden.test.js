// Hidden tests for the large task: only behaviour task.txt states.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as lib from '../src/index.js';

let n = 0;
const ev = (type, actorId, at, extra = {}) => lib.createEvent({ id: `h${++n}`, type, actorId, at, ...extra });

test('H1 actorId field', () => {
  const e = ev('login', 'alice', '2026-01-05T09:00:00Z');
  assert.equal(e.actorId, 'alice');
  assert.equal('userId' in e, false);
});
test('H2 actorId is required, message names it', () => {
  assert.throws(() => lib.createEvent({ id: 'x', type: 'login', at: '2026-01-05T09:00:00Z' }), /actorId/);
});
test('H3 renamed functions exported, old names gone', () => {
  assert.equal(typeof lib.byActor, 'function');
  assert.equal(typeof lib.eventsPerActor, 'function');
  assert.equal(lib.byUser, undefined);
  assert.equal(lib.eventsPerUser, undefined);
});
test('H4 byActor, filter and countBy by actorId', () => {
  const s = lib.createStore();
  lib.append(s, ev('login', 'alice', '2026-01-05T09:00:00Z'));
  lib.append(s, ev('login', 'bob', '2026-01-05T10:00:00Z'));
  assert.equal(lib.byActor(s, 'bob').length, 1);
  assert.equal(lib.filterEvents(lib.all(s), { actorId: 'alice' }).length, 1);
  assert.deepEqual(lib.countBy(lib.all(s), 'actorId'), { alice: 1, bob: 1 });
  assert.equal(lib.eventsPerActor(lib.all(s)), 1);
});
test('H5 sessions and timeline use actorId', () => {
  const events = [ev('login', 'alice', '2026-01-05T09:00:00Z')];
  assert.equal(lib.sessions(events)[0].actorId, 'alice');
  assert.deepEqual(lib.timeline(events, 'alice'), ['09:00 login']);
});
test('H6 severity defaults to info and is validated', () => {
  assert.equal(ev('login', 'a', '2026-01-05T09:00:00Z').severity, 'info');
  assert.equal(ev('login', 'a', '2026-01-05T09:00:00Z', { severity: 'warn' }).severity, 'warn');
  assert.throws(() => ev('login', 'a', '2026-01-05T09:00:00Z', { severity: 'fatal' }));
});
test('H7 minSeverity keeps that level and above', () => {
  const events = ['debug', 'info', 'warn', 'error'].map((s) => ev('x', 'a', '2026-01-05T09:00:00Z', { severity: s }));
  assert.deepEqual(lib.filterEvents(events, { minSeverity: 'warn' }).map((e) => e.severity), ['warn', 'error']);
  assert.throws(() => lib.filterEvents(events, { minSeverity: 'loud' }));
});
test('H8 countBy severity', () => {
  const events = [ev('x', 'a', '2026-01-05T09:00:00Z'), ev('x', 'a', '2026-01-05T09:00:00Z', { severity: 'error' })];
  assert.deepEqual(lib.countBy(events, 'severity'), { info: 1, error: 1 });
});
test('H9 format prefixes warn and error only', () => {
  assert.equal(lib.formatEvent(ev('login', 'alice', '2026-01-05T09:00:00Z', { severity: 'warn' })), '[WARN] 2026-01-05T09:00:00Z actor=alice login');
  assert.equal(lib.formatEvent(ev('login', 'alice', '2026-01-05T09:00:00Z', { severity: 'error' })), '[ERROR] 2026-01-05T09:00:00Z actor=alice login');
  assert.equal(lib.formatEvent(ev('login', 'alice', '2026-01-05T09:00:00Z')), '2026-01-05T09:00:00Z actor=alice login');
});
test('H10 CSV header and round trip', () => {
  assert.equal(lib.CSV_HEADER, 'id,type,actorId,at,severity');
  const events = [ev('login', 'alice', '2026-01-05T09:00:00Z', { severity: 'debug' }), ev('login', 'bob', '2026-01-05T10:00:00Z')];
  assert.deepEqual(lib.parseCsv(lib.toCsv(events)), events);
});
test('H11 CSV empty severity is info', () => {
  assert.equal(lib.parseCsv('id,type,actorId,at,severity\na,login,alice,2026-01-05T09:00:00Z,\n')[0].severity, 'info');
});
test('H12 JSON lines round trip and missing severity', () => {
  const events = [ev('file.read', 'bob', '2026-01-05T09:00:00Z', { severity: 'error', data: { p: 1 } })];
  assert.deepEqual(lib.parseJsonLines(lib.toJsonLines(events)), events);
  const one = lib.parseJsonLines('{"id":"a","type":"login","actorId":"alice","at":"2026-01-05T09:00:00Z"}\n')[0];
  assert.equal(one.severity, 'info');
  assert.equal(one.actorId, 'alice');
});
test('H13 errorRate', () => {
  const events = [ev('x', 'a', '2026-01-05T09:00:00Z', { severity: 'error' }), ev('x', 'a', '2026-01-05T09:00:00Z'), ev('x', 'a', '2026-01-05T09:00:00Z')];
  assert.equal(lib.errorRate(events), 0.33);
});
test('H14 retention drops debug after 7 days', () => {
  const now = '2026-02-01T00:00:00Z';
  const events = [
    ev('x', 'a', '2026-01-20T00:00:00Z', { severity: 'debug' }),
    ev('x', 'a', '2026-01-20T00:00:00Z', { severity: 'info' }),
    ev('x', 'a', '2026-01-28T00:00:00Z', { severity: 'debug' }),
  ];
  assert.deepEqual(lib.applyRetention(events, now).map((e) => e.at + e.severity),
    ['2026-01-20T00:00:00Zinfo', '2026-01-28T00:00:00Zdebug']);
});
test('H15 retention: maxAgeDays still applies to every severity', () => {
  const now = '2026-02-01T00:00:00Z';
  const events = [ev('x', 'a', '2026-01-28T00:00:00Z', { severity: 'debug' }), ev('x', 'a', '2026-01-28T00:00:00Z', { severity: 'error' })];
  assert.equal(lib.applyRetention(events, now, { maxAgeDays: 3 }).length, 0);
});
test('H16 unchanged behaviour', () => {
  const events = [ev('a', 'u', '2026-01-06T09:00:00Z'), ev('a', 'u', '2026-01-05T09:00:00Z')];
  assert.equal(lib.busiestDay(events), '2026-01-05');
  assert.equal(lib.filterEvents(events, { from: '2026-01-06T00:00:00Z' }).length, 1);
});
