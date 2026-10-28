import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CSV_HEADER, parseCsv, toCsv } from '../src/csv.js';

test('parse a CSV with and without years', () => {
  const items = parseCsv(`${CSV_HEADER}\nDune,Frank Herbert,412,1965\nA,B,10,\n`);
  assert.deepEqual(items, [
    { title: 'Dune', author: 'Frank Herbert', pages: 412, year: 1965 },
    { title: 'A', author: 'B', pages: 10, year: null },
  ]);
});

test('parse rejects a wrong header and bad rows with the line number', () => {
  assert.throws(() => parseCsv('name,writer\nA,B'), /header/);
  assert.throws(() => parseCsv(`${CSV_HEADER}\nA,B,ten,`), /line 2: pages/);
  assert.deepEqual(parseCsv(''), []);
});

test('round trip', () => {
  const items = [
    { title: 'Dune', author: 'Frank Herbert', pages: 412, year: 1965 },
    { title: 'A', author: 'B', pages: 10, year: null },
  ];
  assert.equal(toCsv(items), `${CSV_HEADER}\nDune,Frank Herbert,412,1965\nA,B,10,\n`);
  assert.deepEqual(parseCsv(toCsv(items)), items);
});
