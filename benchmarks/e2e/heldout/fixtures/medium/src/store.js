// In-memory catalogue. Prices are integer cents.
const SEED = [
    { sku: 'PEN-BLK', name: 'Black pen', price: 150, stock: 40 },
    { sku: 'PEN-RED', name: 'Red pen', price: 150, stock: 5 },
    { sku: 'NOTE-A5', name: 'A5 notebook', price: 425, stock: 12 },
    { sku: 'BAG-TOTE', name: 'Tote bag', price: 1299, stock: 0 },
];

let products = new Map();

export function reset() {
    products = new Map(SEED.map((p) => [p.sku, { ...p }]));
}

export function listProducts() {
    return [...products.values()].map((p) => ({ ...p }));
}

export function getProduct(sku) {
    const p = products.get(sku);
    return p ? { ...p } : undefined;
}

reset();
