import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filterItems, sortItems } from '../src/query.js';

const items = [
  { id: 1, title: 'Beta', author: 'Ann', pages: 300, year: 2001 },
  { id: 2, title: 'alpha', author: 'Bob', pages: 120, year: null },
  { id: 3, title: 'Gamma', author: 'ann', pages: 450, year: 2001 },
];

test('filter by author ignores case', () => {
  assert.deepEqual(filterItems(items, { author: 'ANN' }).map((i) => i.id), [1, 3]);
});

test('filter by page range and year', () => {
  assert.deepEqual(filterItems(items, { minPages: 200 }).map((i) => i.id), [1, 3]);
  assert.deepEqual(filterItems(items, { maxPages: 300 }).map((i) => i.id), [1, 2]);
  assert.deepEqual(filterItems(items, { minPages: 200, year: 2001, maxPages: 400 }).map((i) => i.id), [1]);
  assert.equal(filterItems(items).length, 3);
});

test('sort by title and pages', () => {
  assert.deepEqual(sortItems(items).map((i) => i.id), [2, 1, 3]);
  assert.deepEqual(sortItems(items, 'pages', 'desc').map((i) => i.id), [3, 1, 2]);
});

test('sort rejects unknown keys and directions', () => {
  assert.throws(() => sortItems(items, 'colour'), /sort key/);
  assert.throws(() => sortItems(items, 'title', 'up'), /direction/);
});
