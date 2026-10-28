import { test } from 'node:test';
import assert from 'node:assert/strict';
import { truncate, wordCount } from '../src/index.js';

test('truncate keeps short text', () => {
  assert.equal(truncate('abc', 5), 'abc');
});

test('truncate adds an ellipsis', () => {
  assert.equal(truncate('abcdef', 4), 'abc…');
});

test('wordCount counts words', () => {
  assert.equal(wordCount('  one two   three '), 3);
  assert.equal(wordCount('   '), 0);
});
