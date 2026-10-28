import { test } from 'node:test';
import assert from 'node:assert/strict';
import { slugify } from '../src/index.js';

test('lower-cases and joins words', () => {
  assert.equal(slugify('Hello World'), 'hello-world');
});

test('collapses runs of other characters', () => {
  assert.equal(slugify('a  &  b'), 'a-b');
});

test('rejects non-strings', () => {
  assert.throws(() => slugify(42), TypeError);
});
