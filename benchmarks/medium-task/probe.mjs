// Edge probe: inputs task.txt doesn't spell out. Pass rules are in PROTOCOL.md (P1-P8).
// usage: node probe.mjs <run dir>
const lib = await import(process.argv[2] + '/src/index.js');
const base = { title: 'Dune', author: 'Frank Herbert', pageCount: 412, year: 1965 };
const unrated = () => lib.createItem(base);

const throws = (fn) => { try { fn(); return false; } catch (e) { return e instanceof Error; } };
// A case passes only if the feature it probes exists; "throws because it isn't there" fails.
const ok = (fn) => { try { return fn(); } catch { return false; } };
const hasRating = ok(() => lib.createItem({ ...base, rating: 3 }).rating === 3);
const hasCsv = ok(() => lib.parseCsv(`${lib.CSV_HEADER}\nA,B,10,2000,3\n`)[0].rating === 3);
const hasAverage = typeof lib.averageRating === 'function';
const hasItem = ok(() => lib.createItem(base).pageCount === 412);
const show = (fn) => { try { const v = fn(); return typeof v === "number" ? String(v) : JSON.stringify(v); } catch (e) { return `throws: ${e.message}`; } };

const cases = [
  ['P1 wrong type: rating "4" (string)', () => {
    if (!hasRating) return false;
    if (throws(() => lib.createItem({ ...base, rating: '4' }))) return true;
    return lib.createItem({ ...base, rating: '4' }).rating === 4;
  }, () => lib.createItem({ ...base, rating: '4' }).rating],
  ['P2 wrong type: rating NaN', () => hasRating && throws(() => lib.createItem({ ...base, rating: NaN })),
    () => lib.createItem({ ...base, rating: NaN }).rating],
  ['P3 wrong type: CSV rating "abc"', () => hasCsv && throws(() => lib.parseCsv(`${lib.CSV_HEADER}\nA,B,10,2000,abc\n`)),
    () => lib.parseCsv(`${lib.CSV_HEADER}\nA,B,10,2000,abc\n`)[0].rating],
  ['P4 negative: CSV rating "-3"', () => hasCsv && throws(() => lib.parseCsv(`${lib.CSV_HEADER}\nA,B,10,2000,-3\n`)),
    () => lib.parseCsv(`${lib.CSV_HEADER}\nA,B,10,2000,-3\n`)[0].rating],
  ['P5 missing: CSV round trip of an unrated item', () => hasCsv && lib.parseCsv(lib.toCsv([unrated()]))[0].rating === null,
    () => lib.parseCsv(lib.toCsv([unrated()]))[0].rating],
  ['P6 empty: averageRating([])', () => hasAverage && (throws(() => lib.averageRating([])) || lib.averageRating([]) === null),
    () => lib.averageRating([])],
  ['P7 empty: averageRating of unrated items only',
    () => hasAverage && hasRating && (throws(() => lib.averageRating([unrated(), unrated()])) || lib.averageRating([unrated(), unrated()]) === null),
    () => lib.averageRating([unrated(), unrated()])],
  ['P8 missing: formatItem of an unrated item', () => {
    if (!hasItem || !hasRating) return false;
    const s = lib.formatItem(unrated());
    return !/null|undefined|NaN|rated/.test(s);
  }, () => lib.formatItem(unrated())],
];

let passed = 0;
for (const [name, pass, value] of cases) {
  let r;
  try { r = pass(); } catch { r = false; }
  if (r) passed++;
  console.log(`${r ? 'PASS' : 'FAIL'} ${name}: ${show(value)}`);
}
console.log(`probe: ${passed}/${cases.length} handled`);
