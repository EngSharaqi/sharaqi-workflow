import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createItem } from '../src/item.js';

test('createItem normalises a valid item', () => {
  const item = createItem({ title: ' Dune ', author: 'Frank Herbert', pages: 412, year: 1965 });
  assert.deepEqual(item, { title: 'Dune', author: 'Frank Herbert', pages: 412, year: 1965 });
});

test('year is optional', () => {
  assert.equal(createItem({ title: 'A', author: 'B', pages: 1 }).year, null);
});

test('createItem rejects bad input', () => {
  assert.throws(() => createItem(null), TypeError);
  assert.throws(() => createItem({ title: '', author: 'B', pages: 1 }), /title/);
  assert.throws(() => createItem({ title: 'A', author: ' ', pages: 1 }), /author/);
  assert.throws(() => createItem({ title: 'A', author: 'B', pages: 0 }), /pages/);
  assert.throws(() => createItem({ title: 'A', author: 'B', pages: 1.5 }), /pages/);
  assert.throws(() => createItem({ title: 'A', author: 'B', pages: 1, year: '1999' }), /year/);
});
