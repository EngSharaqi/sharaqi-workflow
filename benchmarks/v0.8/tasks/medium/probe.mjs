// Edge probe for the medium task: inputs task.txt doesn't spell out. usage: node probe.mjs <run dir>
const lib = await import(process.argv[2] + '/src/index.js');
const val = (fn) => { try { return JSON.stringify(fn()); } catch (e) { return `throws: ${e.message}`; } };
const throws = (fn) => { try { fn(); return false; } catch (e) { return e instanceof Error; } };
const ok = (fn) => { try { return fn(); } catch { return false; } };
const weekly = (createdOn) => lib.createHabit({ name: 'Run', createdOn, frequency: 'weekly' });
// A case counts only if weekly habits exist at all.
const hasWeekly = ok(() => weekly('2026-01-01').frequency === 'weekly');
const hasCsv = ok(() => lib.parseCsv('name,createdOn,frequency\nRun,2026-01-01,weekly\n')[0].frequency === 'weekly');
// 2026 has 53 ISO weeks: 2026-12-27 is Sunday of W52, 2026-12-28 Monday of W53,
// 2027-01-04 Monday of 2027-W01. Three consecutive weeks.
const yearEnd = ['2026-12-27', '2026-12-28', '2027-01-04'];
const cases = [
  ['P1 current streak across the year boundary (week 53)',
    () => hasWeekly && lib.currentStreak(weekly('2026-12-01'), yearEnd, '2027-01-05') === 3,
    () => lib.currentStreak(weekly('2026-12-01'), yearEnd, '2027-01-05')],
  ['P2 longest streak across the year boundary',
    () => hasWeekly && lib.longestStreak(weekly('2026-12-01'), yearEnd) === 3,
    () => lib.longestStreak(weekly('2026-12-01'), yearEnd)],
  ['P3 several check-ins in one week count once',
    () => hasWeekly && lib.completionRate(weekly('2026-01-05'), ['2026-01-05', '2026-01-06', '2026-01-07'], '2026-01-05', '2026-01-11') === 1,
    () => lib.completionRate(weekly('2026-01-05'), ['2026-01-05', '2026-01-06', '2026-01-07'], '2026-01-05', '2026-01-11')],
  ['P4 frequency "Weekly" throws or is stored as weekly',
    () => hasWeekly && (throws(() => lib.createHabit({ name: 'R', createdOn: '2026-01-01', frequency: 'Weekly' }))
      || ok(() => lib.createHabit({ name: 'R', createdOn: '2026-01-01', frequency: 'Weekly' }).frequency === 'weekly')),
    () => lib.createHabit({ name: 'R', createdOn: '2026-01-01', frequency: 'Weekly' }).frequency],
  ['P5 frequency null is daily or throws, never stored as null',
    () => hasWeekly && (throws(() => lib.createHabit({ name: 'R', createdOn: '2026-01-01', frequency: null }))
      || ok(() => lib.createHabit({ name: 'R', createdOn: '2026-01-01', frequency: null }).frequency === 'daily')),
    () => lib.createHabit({ name: 'R', createdOn: '2026-01-01', frequency: null }).frequency],
  ['P6 CSV unknown frequency throws',
    () => hasCsv && throws(() => lib.parseCsv('name,createdOn,frequency\nRun,2026-01-01,monthly\n')),
    () => lib.parseCsv('name,createdOn,frequency\nRun,2026-01-01,monthly\n')],
  ['P7 CSV in the old two-column format: daily habits or a clear error, never frequency undefined',
    () => hasCsv && (throws(() => lib.parseCsv('name,createdOn\nRead,2026-01-01\n'))
      || ok(() => lib.parseCsv('name,createdOn\nRead,2026-01-01\n')[0].frequency === 'daily')),
    () => lib.parseCsv('name,createdOn\nRead,2026-01-01\n')],
  ['P8 weekly format of a zero streak',
    () => hasWeekly && ok(() => lib.formatHabit(weekly('2026-01-01'), 0) === 'Run — streak 0 weeks'),
    () => lib.formatHabit(weekly('2026-01-01'), 0)],
];
let passed = 0;
for (const [name, pass, value] of cases) {
  const r = (() => { try { return pass(); } catch { return false; } })();
  if (r) passed++;
  console.log(`${r ? 'PASS' : 'FAIL'} ${name}: ${val(value)}`);
}
console.log(`probe: ${passed}/${cases.length} handled`);
