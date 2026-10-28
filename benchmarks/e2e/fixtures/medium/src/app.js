import * as store from './store.js';

function send(res, status, body) {
    res.writeHead(status, { 'content-type': 'application/json' });
    res.end(body === undefined ? '' : JSON.stringify(body));
}

function readJson(req) {
    return new Promise((resolve, reject) => {
        let data = '';
        req.on('data', (c) => (data += c));
        req.on('end', () => {
            try {
                resolve(data ? JSON.parse(data) : {});
            } catch {
                reject(new Error('invalid json'));
            }
        });
    });
}

const STATUSES = ['open', 'done'];

export async function handler(req, res) {
    const url = new URL(req.url, 'http://localhost');
    const parts = url.pathname.split('/').filter(Boolean);

    if (parts[0] !== 'tasks') return send(res, 404, { error: { message: 'not found' } });

    if (parts.length === 1 && req.method === 'GET') {
        return send(res, 200, store.all());
    }

    if (parts.length === 1 && req.method === 'POST') {
        let body;
        try {
            body = await readJson(req);
        } catch {
            return send(res, 400, { error: { field: 'body', message: 'invalid json' } });
        }
        if (typeof body.title !== 'string' || !body.title.trim()) {
            return send(res, 400, { error: { field: 'title', message: 'title is required' } });
        }
        if (body.status !== undefined && !STATUSES.includes(body.status)) {
            return send(res, 400, { error: { field: 'status', message: 'invalid status' } });
        }
        return send(res, 201, store.add({ title: body.title.trim(), status: body.status }));
    }

    const id = Number(parts[1]);
    if (parts.length === 2 && Number.isInteger(id)) {
        if (req.method === 'GET') {
            const t = store.find(id);
            return t ? send(res, 200, t) : send(res, 404, { error: { message: 'not found' } });
        }
        if (req.method === 'PATCH') {
            let body;
            try {
                body = await readJson(req);
            } catch {
                return send(res, 400, { error: { field: 'body', message: 'invalid json' } });
            }
            if (body.status !== undefined && !STATUSES.includes(body.status)) {
                return send(res, 400, { error: { field: 'status', message: 'invalid status' } });
            }
            const t = store.update(id, body);
            return t ? send(res, 200, t) : send(res, 404, { error: { message: 'not found' } });
        }
        if (req.method === 'DELETE') {
            return store.remove(id) ? send(res, 204) : send(res, 404, { error: { message: 'not found' } });
        }
    }

    return send(res, 405, { error: { message: 'method not allowed' } });
}
