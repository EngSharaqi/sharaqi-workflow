// Edge probe for the small task: inputs task.txt doesn't spell out. usage: node probe.mjs <run dir>
const { parseDuration, formatDuration } = await import(process.argv[2] + '/src/index.js');
const val = (fn) => { try { return JSON.stringify(fn()); } catch (e) { return `throws: ${e.message}`; } };
const throws = (fn) => { try { fn(); return false; } catch (e) { return e instanceof Error; } };
const eq = (fn, want) => { try { return fn() === want; } catch { return false; } };
// A case counts only if the new units exist, so "throws because d/s aren't supported" fails.
const hasNew = eq(() => parseDuration('1d1s'), 86401);
const cases = [
  ['P1 zero seconds parse to 0', () => eq(() => parseDuration('0s'), 0), () => parseDuration('0s')],
  ['P2 unit without a number throws', () => hasNew && throws(() => parseDuration('d')), () => parseDuration('d')],
  ['P3 negative throws', () => hasNew && throws(() => parseDuration('-5s')), () => parseDuration('-5s')],
  ['P4 decimal throws or is exact', () => hasNew && (throws(() => parseDuration('1.5h')) || eq(() => parseDuration('1.5h'), 5400)), () => parseDuration('1.5h')],
  ['P5 unknown unit throws', () => hasNew && throws(() => parseDuration('3w')), () => parseDuration('3w')],
  ['P6 repeated seconds throws', () => hasNew && throws(() => parseDuration('1s1s')), () => parseDuration('1s1s')],
  ['P7 format still rejects a fraction', () => hasNew && throws(() => formatDuration(1.5)), () => formatDuration(1.5)],
  ['P8 round trip of a large value', () => eq(() => parseDuration(formatDuration(1234567).replace(/ /g, '')), 1234567),
    () => formatDuration(1234567)],
];
let passed = 0;
for (const [name, pass, value] of cases) {
  const r = (() => { try { return pass(); } catch { return false; } })();
  if (r) passed++;
  console.log(`${r ? 'PASS' : 'FAIL'} ${name}: ${val(value)}`);
}
console.log(`probe: ${passed}/${cases.length} handled`);
