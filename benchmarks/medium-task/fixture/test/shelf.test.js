import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Shelf } from '../src/shelf.js';

test('add assigns increasing ids', () => {
  const shelf = new Shelf();
  const a = shelf.add({ title: 'A', author: 'X', pages: 10 });
  const b = shelf.add({ title: 'B', author: 'Y', pages: 20 });
  assert.equal(a.id, 1);
  assert.equal(b.id, 2);
  assert.equal(shelf.size, 2);
});

test('get, remove and list', () => {
  const shelf = new Shelf();
  const a = shelf.add({ title: 'A', author: 'X', pages: 10 });
  assert.equal(shelf.get(a.id).pages, 10);
  assert.equal(shelf.get(99), null);
  assert.equal(shelf.remove(a.id), true);
  assert.equal(shelf.remove(a.id), false);
  assert.deepEqual(shelf.list(), []);
});

test('add validates', () => {
  assert.throws(() => new Shelf().add({ title: 'A', author: 'X', pages: -5 }), /pages/);
});
