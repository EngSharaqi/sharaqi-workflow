// Hidden acceptance tests for tasks/complex.txt. Copied into the run's test/ dir only at scoring time.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { Sheet } from '../src/sheet.js';

const sheet = (cells) => {
    const s = new Sheet();
    for (const [k, v] of Object.entries(cells)) s.set(k, v);
    return s;
};

test('C01 numbers, text, empty, clear', () => {
    const s = sheet({ A1: '3', A2: ' -2.5 ', A3: '1e3', A4: 'hi', A5: ' hi ' });
    assert.equal(s.get('A1'), 3);
    assert.equal(s.get('A2'), -2.5);
    assert.equal(s.get('A3'), 1000);
    assert.equal(s.get('A4'), 'hi');
    assert.equal(s.get('A5'), ' hi ');
    assert.equal(s.get('B7'), null);
    s.set('A1', '');
    assert.equal(s.get('A1'), null);
});

test('C02 case-insensitive references', () => {
    const s = sheet({ a1: '5', B1: '=a1*2' });
    assert.equal(s.get('A1'), 5);
    assert.equal(s.get('b1'), 10);
});

test('C03 invalid references throw RangeError', () => {
    const s = new Sheet();
    for (const r of ['AA1', 'A0', 'A100000', '1A', '']) {
        assert.throws(() => s.get(r), RangeError, `get ${r}`);
    }
    assert.throws(() => s.set('A0', '1'), RangeError);
    assert.equal(s.get('Z99999'), null);
});

test('C04 precedence and associativity', () => {
    const cases = {
        '=1+2*3': 7, '=(1+2)*3': 9, '=2-3-4': -5, '=8/2/2': 2, '=-2*3': -6, '=-(2+3)': -5,
        '=2*-3': -6, '=1+2=3': 1, '=3>=3': 1, '=2<>2': 0, '=1<=0': 0, '=1+(2>1)': 2, '=3.5*2': 7,
    };
    const s = new Sheet();
    for (const [f, want] of Object.entries(cases)) {
        s.set('A1', f);
        assert.equal(s.get('A1'), want, f);
    }
});

test('C05 empty cell is 0 when referenced', () => {
    const s = sheet({ A1: '5', B1: '=A1+B9', C1: '=B9' });
    assert.equal(s.get('B1'), 5);
    assert.equal(s.get('C1'), 0);
});

test('C06 direct reference returns text; operators on text are #VALUE!', () => {
    const s = sheet({ A1: 'hi', B1: '=A1', C1: '=A1+1', D1: '=A1>1', E1: '=-A1' });
    assert.equal(s.get('B1'), 'hi');
    assert.equal(s.get('C1'), '#VALUE!');
    assert.equal(s.get('D1'), '#VALUE!');
    assert.equal(s.get('E1'), '#VALUE!');
});

test('C07 SUM MIN MAX COUNT over ranges and arguments', () => {
    const s = sheet({
        A1: '1', A2: '2', A3: 'x', A5: '4', C1: '1', D1: '10', C2: '2', D2: '20',
        B1: '=SUM(A1:A5)', B2: '=MIN(A1:A5)', B3: '=MAX(A1:A5)', B4: '=COUNT(A1:A5)',
        B5: '=sum(A5:A1)', B6: '=SUM(A1, 10, A1:A2)', B7: '=MIN(A3)', B8: '=MAX(A4, A3)',
        B9: '=COUNT(A3, A4)', B10: '=SUM(D2:C1)', B11: '=MAX(A1:A5) - MIN(A1:A5)',
    });
    assert.equal(s.get('B1'), 7);
    assert.equal(s.get('B2'), 1);
    assert.equal(s.get('B3'), 4);
    assert.equal(s.get('B4'), 3);
    assert.equal(s.get('B5'), 7);
    assert.equal(s.get('B6'), 14);
    assert.equal(s.get('B7'), 0);
    assert.equal(s.get('B8'), 0);
    assert.equal(s.get('B9'), 0);
    assert.equal(s.get('B10'), 33);
    assert.equal(s.get('B11'), 3);
});

test('C08 IF is lazy and needs 3 arguments', () => {
    const s = sheet({
        A1: '=IF(1>0, 10, 20)', A2: '=IF(0, 10, 20)', A3: '=IF(2, 1/0, 5)', A4: '=IF(0, 1/0, 5)',
        A5: '=IF(1, 2)', A6: '=if(1, 2, 3)', A7: '=IF(0, FOO(1), 9)',
    });
    assert.equal(s.get('A1'), 10);
    assert.equal(s.get('A2'), 20);
    assert.equal(s.get('A3'), '#DIV/0!');
    assert.equal(s.get('A4'), 5);
    assert.equal(s.get('A5'), '#PARSE!');
    assert.equal(s.get('A6'), 2);
    assert.equal(s.get('A7'), 9);
});

test('C09 error kinds', () => {
    const cases = {
        '=1/0': '#DIV/0!', '=1/(2-2)': '#DIV/0!', '=FOO(1)': '#NAME?', '=1+': '#PARSE!',
        '=(1': '#PARSE!', '=B1:B2': '#PARSE!', '=1 2': '#PARSE!', '=A0+1': '#REF!', '=AA1': '#REF!',
    };
    const s = new Sheet();
    for (const [f, want] of Object.entries(cases)) {
        s.set('Z1', f);
        assert.equal(s.get('Z1'), want, f);
    }
});

test('C10 error propagation, first error left to right, ranges row by row', () => {
    const s = sheet({
        B1: '=1/0', C1: '=FOO()', D1: '=B1+C1', E1: '=C1+B1', F1: '=SUM(C1, B1)',
        H1: '=1/0', G2: '=XX(1)', I1: '=SUM(G1:H2)', J1: '=B1*0',
    });
    assert.equal(s.get('D1'), '#DIV/0!');
    assert.equal(s.get('E1'), '#NAME?');
    assert.equal(s.get('F1'), '#NAME?');
    assert.equal(s.get('I1'), '#DIV/0!');
    assert.equal(s.get('J1'), '#DIV/0!');
});

test('C11 cycles: static detection, propagation, recovery', () => {
    const s = sheet({
        A1: '=B1', B1: '=A1', C1: '=C1+1', D1: '=A1+1',
        E1: '=SUM(E2:E3)', E3: '=E1', F1: '=IF(1, 5, F2)', F2: '=F1', G1: '=IF(1, 7, A1)',
    });
    for (const r of ['A1', 'B1', 'C1', 'D1', 'E1', 'E3', 'F1', 'F2']) assert.equal(s.get(r), '#CYCLE!', r);
    assert.equal(s.get('G1'), 7);
    s.set('B1', '3');
    assert.equal(s.get('A1'), 3);
    assert.equal(s.get('B1'), 3);
    assert.equal(s.get('D1'), 4);
    s.set('E3', '2');
    assert.equal(s.get('E1'), 2);
});

test('C12 updates propagate, forward references resolve', () => {
    const s = sheet({ A1: '1', B1: '=A1*2', C1: '=B1+A1', X1: '=Y1+1' });
    assert.equal(s.get('C1'), 3);
    s.set('A1', '5');
    assert.equal(s.get('C1'), 15);
    s.set('B1', '');
    assert.equal(s.get('C1'), 5);
    s.set('B1', 'x');
    assert.equal(s.get('C1'), '#VALUE!');
    assert.equal(s.get('X1'), 1);
    s.set('Y1', '4');
    assert.equal(s.get('X1'), 5);
});

test('C13 20,000-cell chain, shuffled, within 2 s', () => {
    const t0 = Date.now();
    const s = new Sheet();
    const n = 20000;
    const order = Array.from({ length: n }, (_, i) => i + 1);
    let seed = 7;
    for (let i = n - 1; i > 0; i--) {
        seed = (seed * 1103515245 + 12345) % 2147483648;
        const j = seed % (i + 1);
        [order[i], order[j]] = [order[j], order[i]];
    }
    for (const r of order) s.set(`A${r}`, r === 1 ? '1' : `=A${r - 1}+1`);
    assert.equal(s.get('A20000'), 20000);
    s.set('A1', '10');
    assert.equal(s.get('A20000'), 20009);
    s.set('B1', '=SUM(A1:A20000)');
    assert.equal(s.get('B1'), 200190000);
    assert.ok(Date.now() - t0 < 2000, `took ${Date.now() - t0} ms`);
});

test('C14 floating point is plain arithmetic', () => {
    const s = sheet({ A1: '=0.1+0.2' });
    assert.ok(Math.abs(s.get('A1') - 0.3) < 1e-12);
});
