import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';

import * as store from '../src/store.js';
import { withServer } from './helpers.js';

beforeEach(() => store.reset());

test('POST creates a task', () =>
    withServer(async (base) => {
        const r = await fetch(`${base}/tasks`, { method: 'POST', body: JSON.stringify({ title: 'a' }) });
        assert.equal(r.status, 201);
        assert.equal((await r.json()).title, 'a');
    }));

test('POST without title is 400', () =>
    withServer(async (base) => {
        const r = await fetch(`${base}/tasks`, { method: 'POST', body: '{}' });
        assert.equal(r.status, 400);
        assert.equal((await r.json()).error.field, 'title');
    }));

test('PATCH and DELETE', () =>
    withServer(async (base) => {
        store.add({ title: 'x' });
        let r = await fetch(`${base}/tasks/1`, { method: 'PATCH', body: JSON.stringify({ status: 'done' }) });
        assert.equal((await r.json()).status, 'done');
        r = await fetch(`${base}/tasks/1`, { method: 'DELETE' });
        assert.equal(r.status, 204);
    }));
