import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatItem, formatList } from '../src/format.js';

test('formatItem with and without a year', () => {
  assert.equal(
    formatItem({ title: 'Dune', author: 'Frank Herbert', pages: 412, year: 1965 }),
    '"Dune" by Frank Herbert, 412 pages (1965)',
  );
  assert.equal(formatItem({ title: 'A', author: 'B', pages: 9, year: null }), '"A" by B, 9 pages');
});

test('formatList numbers the lines', () => {
  const list = formatList([
    { title: 'A', author: 'B', pages: 1, year: null },
    { title: 'C', author: 'D', pages: 2, year: 2000 },
  ]);
  assert.equal(list, '1. "A" by B, 1 pages\n2. "C" by D, 2 pages (2000)');
  assert.equal(formatList([]), 'No items.');
});
