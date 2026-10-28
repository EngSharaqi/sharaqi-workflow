import http from 'node:http';

import { handler } from '../src/app.js';

export async function withServer(fn) {
    const server = http.createServer(handler);
    await new Promise((r) => server.listen(0, r));
    const base = `http://127.0.0.1:${server.address().port}`;
    try {
        return await fn(base);
    } finally {
        await new Promise((r) => server.close(r));
    }
}
