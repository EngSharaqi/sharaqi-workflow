import assert from 'node:assert/strict';
import { test } from 'node:test';

import { Sheet } from '../src/sheet.js';

test('exports a Sheet class', () => {
    assert.equal(typeof Sheet, 'function');
});
