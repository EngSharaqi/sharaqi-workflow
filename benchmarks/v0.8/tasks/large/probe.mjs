// Edge probe for the large task: inputs task.txt doesn't spell out. usage: node probe.mjs <run dir>
const lib = await import(process.argv[2] + '/src/index.js');
const val = (fn) => { try { const v = fn(); return typeof v === 'number' ? String(v) : JSON.stringify(v); } catch (e) { return `throws: ${e.message}`; } };
const throws = (fn) => { try { fn(); return false; } catch (e) { return e instanceof Error; } };
const ok = (fn) => { try { return fn(); } catch { return false; } };
let n = 0;
const ev = (extra = {}, at = '2026-01-05T09:00:00Z') => lib.createEvent({ id: `p${++n}`, type: 'login', actorId: 'alice', at, ...extra });
// A case counts only if the feature it probes exists.
const hasSeverity = ok(() => ev({ severity: 'warn' }).severity === 'warn');
const hasRate = typeof lib.errorRate === 'function';
const hasCsv = ok(() => lib.parseCsv('id,type,actorId,at,severity\na,login,al,2026-01-05T09:00:00Z,warn\n')[0].severity === 'warn');
const hasJson = ok(() => lib.parseJsonLines('{"id":"a","type":"login","actorId":"al","at":"2026-01-05T09:00:00Z","severity":"warn"}\n')[0].severity === 'warn');
const now = '2026-02-01T00:00:00Z';
const cases = [
  ['P1 errorRate([]) is null or throws (0/0 trap)',
    () => hasRate && (throws(() => lib.errorRate([])) || lib.errorRate([]) === null), () => lib.errorRate([])],
  ['P2 debug exactly 7 days old is kept',
    () => hasSeverity && ok(() => lib.applyRetention([ev({ severity: 'debug' }, '2026-01-25T00:00:00Z')], now).length === 1),
    () => lib.applyRetention([ev({ severity: 'debug' }, '2026-01-25T00:00:00Z')], now).length],
  ['P3 severity "WARN" throws or is stored as warn',
    () => hasSeverity && (throws(() => ev({ severity: 'WARN' })) || ok(() => ev({ severity: 'WARN' }).severity === 'warn')),
    () => ev({ severity: 'WARN' }).severity],
  ['P4 CSV unknown severity throws',
    () => hasCsv && throws(() => lib.parseCsv('id,type,actorId,at,severity\na,login,al,2026-01-05T09:00:00Z,fatal\n')),
    () => lib.parseCsv('id,type,actorId,at,severity\na,login,al,2026-01-05T09:00:00Z,fatal\n')],
  ['P5 JSON severity null is info or throws, never stored as null',
    () => hasJson && (throws(() => lib.parseJsonLines('{"id":"a","type":"login","actorId":"al","at":"2026-01-05T09:00:00Z","severity":null}\n'))
      || ok(() => lib.parseJsonLines('{"id":"a","type":"login","actorId":"al","at":"2026-01-05T09:00:00Z","severity":null}\n')[0].severity === 'info')),
    () => lib.parseJsonLines('{"id":"a","type":"login","actorId":"al","at":"2026-01-05T09:00:00Z","severity":null}\n')[0].severity],
  ['P6 minSeverity debug keeps everything',
    () => hasSeverity && ok(() => lib.filterEvents([ev(), ev({ severity: 'debug' }), ev({ severity: 'error' })], { minSeverity: 'debug' }).length === 3),
    () => lib.filterEvents([ev(), ev({ severity: 'debug' }), ev({ severity: 'error' })], { minSeverity: 'debug' }).length],
  ['P7 the old field name alone is rejected',
    () => hasSeverity && throws(() => lib.createEvent({ id: 'x', type: 'login', userId: 'alice', at: '2026-01-05T09:00:00Z' })),
    () => lib.createEvent({ id: 'x', type: 'login', userId: 'alice', at: '2026-01-05T09:00:00Z' })],
  ['P8 info and debug format has no prefix and no "undefined"',
    () => hasSeverity && ok(() => !/\[|undefined/.test(lib.formatEvent(ev({ severity: 'debug' })) + lib.formatEvent(ev()))),
    () => lib.formatEvent(ev({ severity: 'debug' }))],
];
let passed = 0;
for (const [name, pass, value] of cases) {
  const r = (() => { try { return pass(); } catch { return false; } })();
  if (r) passed++;
  console.log(`${r ? 'PASS' : 'FAIL'} ${name}: ${val(value)}`);
}
console.log(`probe: ${passed}/${cases.length} handled`);
