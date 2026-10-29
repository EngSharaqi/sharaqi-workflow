import { send } from './http.js';
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
        return send(res, 404, { error: 'not found' });
    } catch (err) {
        return send(res, 500, { error: 'internal error' });
    }
}
