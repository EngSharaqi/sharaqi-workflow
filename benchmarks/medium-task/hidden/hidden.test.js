// Hidden tests: the behaviour task.txt states. Copied into <run>/hidden-run/ only after a run.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as lib from '../src/index.js';

const base = { title: 'Dune', author: 'Frank Herbert', pageCount: 412, year: 1965 };

test('H1 items carry pageCount, not pages', () => {
  const item = lib.createItem(base);
  assert.equal(item.pageCount, 412);
  assert.equal('pages' in item, false);
});

test('H2 pageCount is validated; the old name is not accepted', () => {
  assert.throws(() => lib.createItem({ ...base, pageCount: 0 }));
  assert.throws(() => lib.createItem({ title: 'A', author: 'B', pages: 10 }));
});

test('H3 stats functions renamed', () => {
  const items = [lib.createItem({ ...base, pageCount: 100 }), lib.createItem({ ...base, pageCount: 205 })];
  assert.equal(lib.totalPageCount(items), 305);
  assert.equal(lib.averagePageCount(items), 152.5);
  assert.equal(lib.averagePageCount([]), null);
  assert.equal(lib.totalPages, undefined);
  assert.equal(lib.averagePages, undefined);
});

test('H4 filter options renamed', () => {
  const items = [100, 200, 300].map((n) => lib.createItem({ ...base, pageCount: n }));
  assert.deepEqual(lib.filterItems(items, { minPageCount: 150 }).map((i) => i.pageCount), [200, 300]);
  assert.deepEqual(lib.filterItems(items, { maxPageCount: 250 }).map((i) => i.pageCount), [100, 200]);
});

test('H5 sort key pageCount; pages is unknown', () => {
  const items = [300, 100, 200].map((n) => lib.createItem({ ...base, pageCount: n }));
  assert.deepEqual(lib.sortItems(items, 'pageCount').map((i) => i.pageCount), [100, 200, 300]);
  assert.throws(() => lib.sortItems(items, 'pages'));
});

test('H6 rating defaults to null', () => {
  assert.equal(lib.createItem(base).rating, null);
});

test('H7 ratings 1 to 5 are accepted', () => {
  for (const r of [1, 2, 3, 4, 5]) assert.equal(lib.createItem({ ...base, rating: r }).rating, r);
});

test('H8 ratings out of range throw', () => {
  for (const r of [0, 6, -1, 100]) assert.throws(() => lib.createItem({ ...base, rating: r }), Error);
});

test('H9 a non-integer rating throws', () => {
  assert.throws(() => lib.createItem({ ...base, rating: 4.5 }), Error);
});

test('H10 CSV header and export carry pageCount and rating', () => {
  assert.equal(lib.CSV_HEADER, 'title,author,pageCount,year,rating');
  const csv = lib.toCsv([lib.createItem({ ...base, rating: 4 })]);
  assert.equal(csv, 'title,author,pageCount,year,rating\nDune,Frank Herbert,412,1965,4\n');
});

test('H11 CSV import reads rating as a number', () => {
  const [item] = lib.parseCsv('title,author,pageCount,year,rating\nDune,Frank Herbert,412,1965,3\n');
  assert.equal(item.rating, 3);
  assert.equal(item.pageCount, 412);
});

test('H12 formatItem appends the rating', () => {
  const s = lib.formatItem(lib.createItem({ ...base, rating: 4 }));
  assert.equal(s, '"Dune" by Frank Herbert, 412 pages (1965) — rated 4/5');
});

test('H13 minRating filter excludes unrated items', () => {
  const items = [lib.createItem({ ...base, rating: 5 }), lib.createItem(base),
    lib.createItem({ ...base, rating: 3 }), lib.createItem({ ...base, rating: 4 })];
  assert.deepEqual(lib.filterItems(items, { minRating: 4 }).map((i) => i.rating), [5, 4]);
  assert.deepEqual(lib.filterItems(items, { minRating: 1 }).map((i) => i.rating), [5, 3, 4]);
});

test('H14 unrated items sort last in both directions', () => {
  const items = [lib.createItem(base), lib.createItem({ ...base, rating: 2 }),
    lib.createItem({ ...base, rating: 5 })];
  assert.deepEqual(lib.sortItems(items, 'rating', 'asc').map((i) => i.rating), [2, 5, null]);
  assert.deepEqual(lib.sortItems(items, 'rating', 'desc').map((i) => i.rating), [5, 2, null]);
});

test('H15 averageRating ignores unrated items and rounds to one decimal', () => {
  const r = (n) => lib.createItem({ ...base, rating: n });
  assert.equal(lib.averageRating([r(4), r(5), lib.createItem(base)]), 4.5);
  assert.equal(lib.averageRating([r(4), r(4), r(5)]), 4.3);
});

test('H16 Shelf keeps the rating', () => {
  const shelf = new lib.Shelf();
  const item = shelf.add({ ...base, rating: 2 });
  assert.equal(shelf.get(item.id).rating, 2);
  assert.equal(shelf.get(item.id).pageCount, 412);
});
