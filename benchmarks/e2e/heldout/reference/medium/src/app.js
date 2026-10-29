import { readJson, send } from './http.js';
import { createOrder, getOrder } from './orders.js';
import { getProduct, listProducts } from './store.js';

export async function handler(req, res) {
    const url = new URL(req.url, 'http://localhost');
    const parts = url.pathname.split('/').filter(Boolean);
    try {
        if (req.method === 'GET' && url.pathname === '/products') {
            return send(res, 200, listProducts());
        }
        if (req.method === 'GET' && parts[0] === 'products' && parts.length === 2) {
            const p = getProduct(decodeURIComponent(parts[1]));
            return p ? send(res, 200, p) : send(res, 404, { error: 'not found' });
        }
        if (req.method === 'POST' && url.pathname === '/orders') {
            let body;
            try {
                body = await readJson(req);
            } catch {
                return send(res, 400, { error: 'invalid JSON' });
            }
            const [status, out] = createOrder(body);
            return send(res, status, out);
        }
        if (req.method === 'GET' && parts[0] === 'orders' && parts.length === 2) {
            const o = getOrder(decodeURIComponent(parts[1]));
            return o ? send(res, 200, o) : send(res, 404, { error: 'not found' });
        }
        return send(res, 404, { error: 'not found' });
    } catch (err) {
        return send(res, 500, { error: 'internal error' });
    }
}
