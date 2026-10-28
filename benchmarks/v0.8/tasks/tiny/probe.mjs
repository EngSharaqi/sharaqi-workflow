// Edge probe for the tiny task: inputs task.txt doesn't spell out. usage: node probe.mjs <run dir>
const { slugify } = await import(process.argv[2] + '/src/index.js');
const val = (fn) => { try { return JSON.stringify(fn()); } catch (e) { return `throws: ${e.message}`; } };
const eq = (fn, want) => { try { return fn() === want; } catch { return false; } };
const cases = [
  ['P1 empty string gives empty slug', () => eq(() => slugify(''), ''), () => slugify('')],
  ['P2 only punctuation gives empty slug', () => eq(() => slugify('?!'), ''), () => slugify('?!')],
  ['P3 only spaces gives empty slug', () => eq(() => slugify('   '), ''), () => slugify('   ')],
  ['P4 hyphens in the input are not doubled', () => eq(() => slugify('-a--b-'), 'a-b'), () => slugify('-a--b-')],
];
let passed = 0;
for (const [name, pass, value] of cases) {
  const r = (() => { try { return pass(); } catch { return false; } })();
  if (r) passed++;
  console.log(`${r ? 'PASS' : 'FAIL'} ${name}: ${val(value)}`);
}
console.log(`probe: ${passed}/${cases.length} handled`);
