import { test } from 'node:test';
import assert from 'node:assert/strict';
import { totalPages, averagePages, countByAuthor } from '../src/stats.js';

const items = [
  { title: 'A', author: 'Ann', pages: 100, year: null },
  { title: 'B', author: 'Bob', pages: 205, year: null },
  { title: 'C', author: 'Ann', pages: 50, year: null },
];

test('totals and averages', () => {
  assert.equal(totalPages(items), 355);
  assert.equal(averagePages(items), 118.3);
});

test('average of an empty list is null', () => {
  assert.equal(totalPages([]), 0);
  assert.equal(averagePages([]), null);
});

test('count by author', () => {
  assert.deepEqual(countByAuthor(items), { Ann: 2, Bob: 1 });
});
