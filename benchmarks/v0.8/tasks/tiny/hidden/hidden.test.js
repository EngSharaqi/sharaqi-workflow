// Hidden tests for the tiny task: only behaviour task.txt states.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { slugify, truncate, wordCount } from '../src/index.js';

test('H1 trailing punctuation', () => assert.equal(slugify('Hello, World!'), 'hello-world'));
test('H2 leading and trailing spaces', () => assert.equal(slugify('  Hi there  '), 'hi-there'));
test('H3 leading punctuation', () => assert.equal(slugify('...and more'), 'and-more'));
test('H4 unchanged inside', () => assert.equal(slugify('a  &  b'), 'a-b'));
test('H5 already clean', () => assert.equal(slugify('already-fine'), 'already-fine'));
test('H6 still rejects non-strings', () => assert.throws(() => slugify(null), TypeError));
test('H7 other helpers untouched', () => {
  assert.equal(truncate('abcdef', 4), 'abc…');
  assert.equal(wordCount('one two'), 2);
});
