// In-memory task store. `created` is an ISO timestamp; ids are sequential.
let nextId = 1;
const tasks = [];

export function reset(seed = []) {
    tasks.length = 0;
    nextId = 1;
    for (const t of seed) add(t);
}

export function add({ title, status = 'open', created } = {}) {
    const task = { id: nextId++, title, status, created: created ?? new Date().toISOString() };
    tasks.push(task);
    return task;
}

export function all() {
    return tasks.slice();
}

export function find(id) {
    return tasks.find((t) => t.id === id);
}

export function update(id, fields) {
    const t = find(id);
    if (!t) return undefined;
    Object.assign(t, fields);
    return t;
}

export function remove(id) {
    const i = tasks.findIndex((t) => t.id === id);
    if (i === -1) return false;
    tasks.splice(i, 1);
    return true;
}
