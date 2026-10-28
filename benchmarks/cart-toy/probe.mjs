// Invalid / missing coupon values: each must throw or return a finite number, never NaN.
const { applyCoupon, total } = await import(process.argv[2] + '/src/cart.js');
const items = [{ price: 1000, qty: 2 }, { price: 500, qty: 1 }];
const cases = [
  ['percent, value missing', () => applyCoupon(1000, { type: 'percent' })],
  ['fixed, value missing', () => applyCoupon(1000, { type: 'fixed' })],
  ['percent, value "abc"', () => applyCoupon(1000, { type: 'percent', value: 'abc' })],
  ['fixed, value "abc"', () => applyCoupon(1000, { type: 'fixed', value: 'abc' })],
  ['fixed, value NaN', () => total(items, { type: 'fixed', value: NaN })],
];
let ok = 0;
for (const [name, fn] of cases) {
  let r;
  try { r = fn(); r = Number.isFinite(r) ? `returns ${r}` : `returns ${r} (BAD)`; } catch (e) { r = `throws: ${e.message}`; }
  if (!r.includes('BAD')) ok++;
  console.log(`${name}: ${r}`);
}
console.log(`probe: ${ok}/${cases.length} handled`);
