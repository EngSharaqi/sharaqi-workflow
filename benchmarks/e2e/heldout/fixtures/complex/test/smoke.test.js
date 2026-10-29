import assert from 'node:assert/strict';
import { test } from 'node:test';

import { resolve } from '../src/resolve.js';

test('exports resolve', () => {
    assert.equal(typeof resolve, 'function');
});
