import { test } from 'node:test';
import assert from 'node:assert/strict';
import { subtotal, total } from '../src/cart.js';

const items = [{ price: 1000, qty: 2 }, { price: 500, qty: 1 }];

test('subtotal sums price * qty', () => {
    assert.equal(subtotal(items), 2500);
});

test('percent coupon', () => {
    assert.equal(total(items, { type: 'percent', value: 10 }), 2250);
});
