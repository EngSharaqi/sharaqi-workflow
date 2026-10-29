// Hidden acceptance tests for the resolver task. Each case has one answer under the stated rules.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { resolve } from '../src/resolve.js';

const vs = (...versions) => Object.fromEntries(versions.map((v) => [v, {}]));

test('hidden: exact and = pick that version', () => {
    const reg = { a: vs('1.0.0', '1.2.3', '2.0.0'), b: vs('1.0.0', '1.1.0') };
    assert.deepEqual(resolve(reg, { a: '1.2.3', b: '=1.0.0' }), { a: '1.2.3', b: '1.0.0' });
});

test('hidden: caret takes the newest in the major', () => {
    const reg = { a: vs('1.2.3', '1.4.0', '1.9.9', '2.0.0') };
    assert.deepEqual(resolve(reg, { a: '^1.2.3' }), { a: '1.9.9' });
});

test('hidden: caret with zero major and zero minor', () => {
    const reg = { a: vs('0.2.3', '0.2.9', '0.3.0'), b: vs('0.0.3', '0.0.4') };
    assert.deepEqual(resolve(reg, { a: '^0.2.3', b: '^0.0.3' }), { a: '0.2.9', b: '0.0.3' });
});

test('hidden: tilde, comparators, star, ||', () => {
    const reg = { a: vs('1.2.3', '1.2.9', '1.3.0'), b: vs('1.1.0', '1.4.0', '1.5.0'), c: vs('0.1.0', '7.0.0'),
        d: vs('1.5.0', '2.0.0', '3.1.0', '4.0.0') };
    assert.deepEqual(resolve(reg, { a: '~1.2.3', b: '>=1.2.0 <1.5.0', c: '*', d: '^1.0.0 || ^3.0.0' }),
        { a: '1.2.9', b: '1.4.0', c: '7.0.0', d: '3.1.0' });
    assert.deepEqual(resolve(reg, { b: '>1.1.0', d: '<=2.0.0' }), { b: '1.5.0', d: '2.0.0' });
    assert.deepEqual(resolve(reg, { b: '  >=1.0.0   <1.4.0 ', d: '^4.0.0||^1.0.0' }), { b: '1.1.0', d: '4.0.0' });
});

test('hidden: versions compare numerically', () => {
    const reg = { a: vs('1.9.0', '1.10.0', '1.2.0') };
    assert.deepEqual(resolve(reg, { a: '^1.0.0' }), { a: '1.10.0' });
});

test('hidden: transitive dependencies are included', () => {
    const reg = { app: { '1.0.0': { lib: '^2.0.0' } }, lib: { '2.0.0': { util: '~1.0.0' }, '2.3.0': { util: '~1.0.0' } },
        util: vs('1.0.0', '1.0.5', '1.1.0') };
    assert.deepEqual(resolve(reg, { app: '*' }), { app: '1.0.0', lib: '2.3.0', util: '1.0.5' });
});

test('hidden: a shared dependency satisfies every range on it', () => {
    const reg = { a: { '1.0.0': { c: '>=1.2.0' } }, b: { '1.0.0': { c: '<1.5.0' } }, c: vs('1.0.0', '1.3.0', '1.4.0', '1.6.0') };
    assert.deepEqual(resolve(reg, { a: '*', b: '*' }), { a: '1.0.0', b: '1.0.0', c: '1.4.0' });
});

test('hidden: backtracks to an older version when the newest conflicts', () => {
    const reg = { a: { '1.0.0': { c: '^1.0.0' }, '2.0.0': { c: '^2.0.0' } }, c: vs('1.0.0', '2.0.0') };
    assert.deepEqual(resolve(reg, { c: '^1.0.0', a: '*' }), { c: '1.0.0', a: '1.0.0' });
});

test('hidden: backtracks across a later package', () => {
    // a@2 needs b ^2, but b@2 needs c ^2 while root pins c ^1 → a@2 is impossible; a@1 works.
    const reg = { a: { '2.0.0': { b: '^2.0.0' }, '1.0.0': { b: '^1.0.0' } },
        b: { '2.0.0': { c: '^2.0.0' }, '1.0.0': { c: '^1.0.0' } }, c: vs('1.0.0', '2.0.0') };
    assert.deepEqual(resolve(reg, { a: '*', c: '^1.0.0' }), { a: '1.0.0', c: '1.0.0', b: '1.0.0' });
});

test('hidden: earlier packages get the newer version on a trade-off', () => {
    const reg = { a: { '2.0.0': { b: '^1.0.0' }, '1.0.0': {} }, b: vs('1.0.0', '2.0.0') };
    assert.deepEqual(resolve(reg, { a: '*', b: '*' }), { a: '2.0.0', b: '1.0.0' });
});

test('hidden: dependencies of rejected versions are left out', () => {
    const reg = { a: { '2.0.0': { x: '*', c: '^2.0.0' }, '1.0.0': { c: '^1.0.0' } }, c: vs('1.0.0', '2.0.0'), x: vs('1.0.0') };
    const out = resolve(reg, { c: '^1.0.0', a: '*' });
    assert.deepEqual(out, { c: '1.0.0', a: '1.0.0' });
    assert.ok(!('x' in out));
});

test('hidden: cycles resolve', () => {
    const reg = { a: { '1.0.0': { b: '^1.0.0' } }, b: { '1.0.0': { a: '^1.0.0' }, '1.1.0': { a: '^1.0.0' } } };
    assert.deepEqual(resolve(reg, { a: '*' }), { a: '1.0.0', b: '1.1.0' });
});

test('hidden: a version needing a missing package is skipped', () => {
    const reg = { a: { '2.0.0': { ghost: '*' }, '1.0.0': {} } };
    assert.deepEqual(resolve(reg, { a: '*' }), { a: '1.0.0' });
});

test('hidden: missing root dependency is ENOTFOUND', () => {
    const err = (() => { try { resolve({ a: vs('1.0.0') }, { a: '*', nope: '^1.0.0' }); } catch (e) { return e; } })();
    assert.ok(err instanceof Error);
    assert.equal(err.code, 'ENOTFOUND');
    assert.equal(err.package, 'nope');
});

test('hidden: no solution is ERESOLVE naming a package', () => {
    const cases = [
        [{ a: vs('1.0.0') }, { a: '^2.0.0' }, ['a']],
        [{ a: { '1.0.0': { c: '^1.0.0' } }, b: { '1.0.0': { c: '^2.0.0' } }, c: vs('1.0.0', '2.0.0') }, { a: '*', b: '*' }, ['a', 'b', 'c']],
        [{ a: { '1.0.0': { ghost: '*' } } }, { a: '*' }, ['a', 'ghost']],
    ];
    for (const [reg, root, names] of cases) {
        const err = (() => { try { resolve(reg, root); } catch (e) { return e; } })();
        assert.ok(err instanceof Error, JSON.stringify(root));
        assert.equal(err.code, 'ERESOLVE', JSON.stringify(root));
        assert.ok(names.some((n) => err.message.includes(n)), err.message);
    }
});

test('hidden: invalid ranges throw TypeError with the range', () => {
    const reg = { a: vs('1.0.0') };
    for (const r of ['1.2', '^x', '>=', '', '^1.0.0 ||', 'latest']) {
        assert.throws(() => resolve(reg, { a: r }), (e) => e instanceof TypeError && e.message.includes(r), JSON.stringify(r));
    }
    const dep = { a: { '1.0.0': { b: '^x' } }, b: vs('1.0.0') };
    assert.throws(() => resolve(dep, { a: '*' }), (e) => e instanceof TypeError && e.message.includes('^x'));
});

test('hidden: invalid root range wins over a missing package', () => {
    assert.throws(() => resolve({}, { nope: '*', a: '^x' }), TypeError);
});

test('hidden: inputs are not mutated and the result is a fresh object', () => {
    const reg = { a: { '1.0.0': { b: '^1.0.0' } }, b: vs('1.0.0', '1.1.0') };
    const root = { a: '*' };
    const before = JSON.stringify([reg, root]);
    const out = resolve(reg, root);
    assert.equal(JSON.stringify([reg, root]), before);
    assert.notEqual(out, root);
    assert.deepEqual(resolve({}, {}), {});
});

test('hidden: 30 packages × 20 versions resolve quickly', () => {
    const reg = {};
    for (let i = 0; i < 30; i++) {
        reg[`p${i}`] = {};
        for (let v = 0; v < 20; v++) reg[`p${i}`][`1.${v}.0`] = i < 29 ? { [`p${i + 1}`]: `>=1.${Math.min(v, 5)}.0` } : {};
    }
    const t0 = Date.now();
    const out = resolve(reg, { p0: '^1.0.0' });
    assert.ok(Date.now() - t0 < 1000);
    assert.equal(Object.keys(out).length, 30);
    assert.ok(Object.values(out).every((v) => v === '1.19.0'));
});
