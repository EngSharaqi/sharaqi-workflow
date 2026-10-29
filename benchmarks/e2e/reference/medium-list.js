// Reference GET /tasks list logic, used only to validate hidden/medium. Not shown to either arm.
const SORTS = { created: 1, '-created': 1, title: 1, '-title': 1 };

function int(v, field, min, max) {
    if (!/^\d+$/.test(v)) throw { field, message: `${field} must be an integer` };
    const n = Number(v);
    if (n < min || n > max) throw { field, message: `${field} must be between ${min} and ${max}` };
    return n;
}

export function list(all, params) {
    const status = params.get('status');
    if (status !== null && status !== 'open' && status !== 'done') throw { field: 'status', message: 'invalid status' };
    const sort = params.get('sort') ?? 'created';
    if (!SORTS[sort]) throw { field: 'sort', message: 'invalid sort' };
    const page = params.has('page') ? int(params.get('page'), 'page', 1, Infinity) : 1;
    const limit = params.has('limit') ? int(params.get('limit'), 'limit', 1, 100) : 20;
    const q = (params.get('q') ?? '').toLowerCase();
    let rows = all.filter((t) => (status === null || t.status === status) && t.title.toLowerCase().includes(q));
    const key = sort.replace('-', '');
    const dir = sort.startsWith('-') ? -1 : 1;
    rows.sort((a, b) => {
        const x = key === 'title' ? a.title.toLowerCase() : a.created;
        const y = key === 'title' ? b.title.toLowerCase() : b.created;
        return (x < y ? -1 : x > y ? 1 : 0) * dir || a.id - b.id;
    });
    const total = rows.length;
    return { items: rows.slice((page - 1) * limit, page * limit), page, limit, total, totalPages: Math.ceil(total / limit) };
}
