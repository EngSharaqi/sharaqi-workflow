// Shopping cart totals. Prices are in cents.

export function subtotal(items) {
    return items.reduce((sum, item) => sum + item.price * item.qty, 0);
}

export function applyCoupon(amount, coupon) {
    if (!coupon) return amount;
    if (coupon.type === 'percent') {
        return amount - Math.round((amount * coupon.value) / 100);
    }
    throw new Error(`Unknown coupon type: ${coupon.type}`);
}

export function total(items, coupon, taxRate = 0) {
    const discounted = applyCoupon(subtotal(items), coupon);
    return discounted + Math.round(discounted * taxRate);
}
