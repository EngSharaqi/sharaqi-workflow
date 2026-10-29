import { getProduct, takeStock } from './store.js';

const orders = new Map();
let seq = 0;

export function resetOrders() {
    orders.clear();
    seq = 0;
}

export function createOrder(body) {
    const items = body?.items;
    if (!Array.isArray(items) || items.length === 0) return [400, { error: 'items must be a non-empty array' }];
    for (const it of items) {
        if (!it || typeof it.sku !== 'string' || it.sku === '') return [400, { error: 'bad sku' }];
        if (!Number.isInteger(it.qty) || it.qty <= 0) return [400, { error: 'bad qty' }];
    }
    const merged = new Map();
    for (const it of items) merged.set(it.sku, (merged.get(it.sku) ?? 0) + it.qty);
    for (const sku of merged.keys()) if (!getProduct(sku)) return [404, { error: 'unknown sku', sku }];
    for (const [sku, qty] of merged) {
        const p = getProduct(sku);
        if (p.stock < qty) return [409, { error: 'insufficient stock', sku, available: p.stock }];
    }
    const lines = [...merged].map(([sku, qty]) => ({ sku, qty, price: getProduct(sku).price }));
    for (const l of lines) takeStock(l.sku, l.qty);
    const order = { id: String(++seq), items: lines, total: lines.reduce((t, l) => t + l.price * l.qty, 0) };
    orders.set(order.id, order);
    return [201, order];
}

export function getOrder(id) {
    return orders.get(id);
}
