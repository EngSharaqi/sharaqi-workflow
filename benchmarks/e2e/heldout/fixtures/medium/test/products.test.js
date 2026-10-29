import assert from 'node:assert/strict';
import { test } from 'node:test';

import { withServer } from './helpers.js';

test('lists products', () =>
    withServer(async (base) => {
        const r = await fetch(`${base}/products`);
        assert.equal(r.status, 200);
        assert.equal((await r.json()).length, 4);
    }));

test('gets one product or 404', () =>
    withServer(async (base) => {
        assert.equal((await (await fetch(`${base}/products/PEN-RED`)).json()).stock, 5);
        assert.equal((await fetch(`${base}/products/NOPE`)).status, 404);
    }));
