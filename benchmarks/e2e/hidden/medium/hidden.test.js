// Hidden acceptance tests for tasks/medium.txt. Copied into the run's test/ dir only at scoring time.
import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';

import * as store from '../src/store.js';
import { withServer } from './helpers.js';

const seed = [
    { title: 'Write report', status: 'open', created: '2026-01-03T00:00:00.000Z' },
    { title: 'buy milk', status: 'done', created: '2026-01-01T00:00:00.000Z' },
    { title: 'Apple pie', status: 'open', created: '2026-01-02T00:00:00.000Z' },
    { title: 'apple juice', status: 'done', created: '2026-01-02T00:00:00.000Z' },
    { title: 'Report bug', status: 'open', created: '2026-01-05T00:00:00.000Z' },
];

beforeEach(() => store.reset(seed));

const get = (base, qs) => fetch(`${base}/tasks${qs}`).then(async (r) => ({ s: r.status, b: await r.json() }));
const ids = (b) => b.items.map((t) => t.id);

test('H01 default shape and order (created asc, ties by id)', () =>
    withServer(async (base) => {
        const { s, b } = await get(base, '');
        assert.equal(s, 200);
        assert.deepEqual(ids(b), [2, 3, 4, 1, 5]);
        assert.equal(b.page, 1);
        assert.equal(b.limit, 20);
        assert.equal(b.total, 5);
        assert.equal(b.totalPages, 1);
    }));

test('H02 status filter', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?status=done');
        assert.deepEqual(ids(b), [2, 4]);
        assert.equal(b.total, 2);
    }));

test('H03 q is case-insensitive substring', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?q=REPORT');
        assert.deepEqual(ids(b), [1, 5]);
    }));

test('H04 empty q means no filter', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?q=');
        assert.equal(b.total, 5);
    }));

test('H05 sort=title is case-insensitive', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?sort=title');
        assert.deepEqual(ids(b), [4, 3, 2, 5, 1]);
    }));

test('H06 sort=-title', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?sort=-title');
        assert.deepEqual(ids(b), [1, 5, 2, 3, 4]);
    }));

test('H07 sort=-created, ties by id ascending', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?sort=-created');
        assert.deepEqual(ids(b), [5, 1, 3, 4, 2]);
    }));

test('H08 pagination', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?limit=2&page=2');
        assert.deepEqual(ids(b), [4, 1]);
        assert.equal(b.totalPages, 3);
        assert.equal(b.total, 5);
        assert.equal(b.page, 2);
        assert.equal(b.limit, 2);
    }));

test('H09 page past the end is empty 200', () =>
    withServer(async (base) => {
        const { s, b } = await get(base, '?limit=2&page=9');
        assert.equal(s, 200);
        assert.deepEqual(b.items, []);
        assert.equal(b.total, 5);
    }));

test('H10 no match: totalPages 0', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?q=zzz');
        assert.equal(b.total, 0);
        assert.equal(b.totalPages, 0);
        assert.deepEqual(b.items, []);
    }));

test('H11 combined filters + sort + page', () =>
    withServer(async (base) => {
        const { b } = await get(base, '?status=open&q=e&sort=-title&limit=1&page=2');
        // open with "e": Write report(1), Apple pie(3), Report bug(5); -title: 1,5,3
        assert.deepEqual(ids(b), [5]);
        assert.equal(b.total, 3);
        assert.equal(b.totalPages, 3);
    }));

for (const [qs, field] of [
    ['?status=closed', 'status'],
    ['?sort=id', 'sort'],
    ['?page=0', 'page'],
    ['?page=2.5', 'page'],
    ['?page=abc', 'page'],
    ['?limit=0', 'limit'],
    ['?limit=101', 'limit'],
    ['?limit=1.5', 'limit'],
]) {
    test(`H12 invalid ${qs} -> 400 field ${field}`, () =>
        withServer(async (base) => {
            const { s, b } = await get(base, qs);
            assert.equal(s, 400);
            assert.equal(b.error.field, field);
            assert.equal(typeof b.error.message, 'string');
        }));
}

test('H13 limit boundaries 1 and 100 are valid', () =>
    withServer(async (base) => {
        assert.equal((await get(base, '?limit=1')).b.items.length, 1);
        assert.equal((await get(base, '?limit=100')).s, 200);
    }));

test('H14 unknown params ignored', () =>
    withServer(async (base) => {
        const { s, b } = await get(base, '?foo=bar');
        assert.equal(s, 200);
        assert.equal(b.total, 5);
    }));

test('H15 other routes unchanged', () =>
    withServer(async (base) => {
        let r = await fetch(`${base}/tasks/3`);
        assert.equal((await r.json()).title, 'Apple pie');
        r = await fetch(`${base}/tasks`, { method: 'POST', body: JSON.stringify({ title: ' new ' }) });
        assert.equal(r.status, 201);
        assert.equal((await r.json()).title, 'new');
        r = await fetch(`${base}/tasks/99`);
        assert.equal(r.status, 404);
    }));
