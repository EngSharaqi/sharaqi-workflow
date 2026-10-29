export function send(res, status, body) {
    const data = body === undefined ? '' : JSON.stringify(body);
    res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
    res.end(data);
}

export async function readJson(req) {
    let raw = '';
    for await (const chunk of req) raw += chunk;
    if (!raw) return undefined;
    return JSON.parse(raw);
}
