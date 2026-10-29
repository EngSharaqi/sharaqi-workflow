// Hidden acceptance tests for the orders task. Each test reads stock before acting and checks
// deltas, so it doesn't depend on how (or whether) the arm resets state between tests.
import assert from 'node:assert/strict';
import http from 'node:http';
import { after, before, test } from 'node:test';

import { handler } from '../src/app.js';

let server, base;
before(async () => {
    server = http.createServer(handler);
    await new Promise((r) => server.listen(0, r));
    base = `http://127.0.0.1:${server.address().port}`;
});
after(() => new Promise((r) => server.close(r)));

const post = (body, raw = false) =>
    fetch(`${base}/orders`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: raw ? body : JSON.stringify(body),
    });
const stock = async (sku) => (await (await fetch(`${base}/products/${sku}`)).json()).stock;

test('hidden: one line succeeds, 201, stock goes down', async () => {
    const s0 = await stock('PEN-BLK');
    const r = await post({ items: [{ sku: 'PEN-BLK', qty: 2 }] });
    assert.equal(r.status, 201);
    const o = await r.json();
    assert.equal(typeof o.id, 'string');
    assert.ok(o.id.length > 0);
    assert.deepEqual(o.items, [{ sku: 'PEN-BLK', qty: 2, price: 150 }]);
    assert.equal(o.total, 300);
    assert.equal(await stock('PEN-BLK'), s0 - 2);
});

test('hidden: same sku lines merge in first-seen order', async () => {
    const r = await post({ items: [{ sku: 'PEN-BLK', qty: 2 }, { sku: 'NOTE-A5', qty: 1 }, { sku: 'PEN-BLK', qty: 3 }] });
    assert.equal(r.status, 201);
    const o = await r.json();
    assert.deepEqual(o.items, [{ sku: 'PEN-BLK', qty: 5, price: 150 }, { sku: 'NOTE-A5', qty: 1, price: 425 }]);
    assert.equal(o.total, 1175);
});

test('hidden: GET /orders/:id returns the order; unknown id is 404', async () => {
    const o = await (await post({ items: [{ sku: 'NOTE-A5', qty: 1 }] })).json();
    const r = await fetch(`${base}/orders/${encodeURIComponent(o.id)}`);
    assert.equal(r.status, 200);
    assert.deepEqual(await r.json(), o);
    const m = await fetch(`${base}/orders/does-not-exist`);
    assert.equal(m.status, 404);
    assert.deepEqual(await m.json(), { error: 'not found' });
});

test('hidden: two orders get different ids', async () => {
    const a = await (await post({ items: [{ sku: 'PEN-BLK', qty: 1 }] })).json();
    const b = await (await post({ items: [{ sku: 'PEN-BLK', qty: 1 }] })).json();
    assert.notEqual(a.id, b.id);
});

test('hidden: 400 for bad bodies, nothing changes', async () => {
    const s0 = await stock('PEN-BLK');
    const bad = [
        ['{not json', true], [{}], [{ items: 'x' }], [{ items: {} }], [{ items: [] }],
        [{ items: [null] }], [{ items: [{ sku: '', qty: 1 }] }], [{ items: [{ sku: 5, qty: 1 }] }],
        [{ items: [{ qty: 1 }] }], [{ items: [{ sku: 'PEN-BLK', qty: 0 }] }],
        [{ items: [{ sku: 'PEN-BLK', qty: -1 }] }], [{ items: [{ sku: 'PEN-BLK', qty: 1.5 }] }],
        [{ items: [{ sku: 'PEN-BLK', qty: '2' }] }], [{ items: [{ sku: 'PEN-BLK' }] }],
        [{ items: [{ sku: 'PEN-BLK', qty: 1 }, { sku: 'PEN-BLK', qty: 0 }] }],
    ];
    for (const [body, raw] of bad) {
        const r = await post(body, raw);
        assert.equal(r.status, 400, JSON.stringify(body));
        assert.equal(typeof (await r.json()).error, 'string', JSON.stringify(body));
    }
    assert.equal(await stock('PEN-BLK'), s0);
});

test('hidden: 404 names the first unknown sku, nothing changes', async () => {
    const s0 = await stock('PEN-BLK');
    const r = await post({ items: [{ sku: 'PEN-BLK', qty: 1 }, { sku: 'NOPE-1', qty: 1 }, { sku: 'NOPE-2', qty: 1 }] });
    assert.equal(r.status, 404);
    assert.deepEqual(await r.json(), { error: 'unknown sku', sku: 'NOPE-1' });
    assert.equal(await stock('PEN-BLK'), s0);
});

test('hidden: 409 with available count; out-of-stock item', async () => {
    const r = await post({ items: [{ sku: 'BAG-TOTE', qty: 1 }] });
    assert.equal(r.status, 409);
    assert.deepEqual(await r.json(), { error: 'insufficient stock', sku: 'BAG-TOTE', available: 0 });
});

test('hidden: 409 counts same-sku lines together', async () => {
    const s = await stock('PEN-RED');
    assert.ok(s >= 2);
    const r = await post({ items: [{ sku: 'PEN-RED', qty: s - 1 }, { sku: 'PEN-RED', qty: 2 }] });
    assert.equal(r.status, 409);
    assert.deepEqual(await r.json(), { error: 'insufficient stock', sku: 'PEN-RED', available: s });
    assert.equal(await stock('PEN-RED'), s);
});

test('hidden: all-or-nothing when a later line fails', async () => {
    const b0 = await stock('PEN-BLK');
    const n0 = await stock('NOTE-A5');
    const r = await post({ items: [{ sku: 'PEN-BLK', qty: 1 }, { sku: 'NOTE-A5', qty: n0 + 1 }] });
    assert.equal(r.status, 409);
    assert.equal(await stock('PEN-BLK'), b0);
    assert.equal(await stock('NOTE-A5'), n0);
});

test('hidden: check order 400 → 404 → 409', async () => {
    let r = await post({ items: [{ sku: 'NOPE', qty: 1 }, { sku: 'PEN-BLK', qty: 0 }] });
    assert.equal(r.status, 400);
    r = await post({ items: [{ sku: 'PEN-RED', qty: 9999 }, { sku: 'NOPE', qty: 1 }] });
    assert.equal(r.status, 404);
    r = await post({ items: [{ sku: 'PEN-RED', qty: 9999 }, { sku: 'BAG-TOTE', qty: 1 }] });
    assert.equal(r.status, 409);
    assert.equal((await r.json()).sku, 'PEN-RED');
});

test('hidden: existing endpoints still work', async () => {
    const r = await fetch(`${base}/products`);
    assert.equal(r.status, 200);
    assert.equal((await r.json()).length, 4);
    assert.equal((await fetch(`${base}/products/NOPE`)).status, 404);
    assert.equal((await fetch(`${base}/nothing`)).status, 404);
});
