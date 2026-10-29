// Reference engine for tasks/complex.txt, used only to validate hidden/complex. Not shown to either arm.
const ERR = (code) => ({ err: code });
const isErr = (v) => v !== null && typeof v === 'object' && 'err' in v;
const EMPTY = Symbol('empty');
const MAXROW = 99999;

function parseRef(s) {
    const m = /^([A-Za-z]+)(\d+)$/.exec(s);
    if (!m) return null;
    const row = Number(m[2]);
    if (m[1].length !== 1 || row < 1 || row > MAXROW) return null;
    return { col: m[1].toUpperCase().charCodeAt(0) - 65, row };
}
const key = (c, r) => String.fromCharCode(65 + c) + r;

function norm(ref) {
    const p = typeof ref === 'string' ? parseRef(ref) : null;
    if (!p) throw new RangeError(`invalid reference: ${ref}`);
    return key(p.col, p.row);
}

class ParseError extends Error {}

function tokenize(src) {
    const out = [];
    let i = 0;
    while (i < src.length) {
        const ch = src[i];
        if (/\s/.test(ch)) { i++; continue; }
        let m;
        if ((m = /^\d+(\.\d+)?/.exec(src.slice(i)))) { out.push({ t: 'num', v: Number(m[0]) }); i += m[0].length; continue; }
        if ((m = /^[A-Za-z]+\d*/.exec(src.slice(i)))) {
            const w = m[0];
            i += w.length;
            if (/\d/.test(w)) out.push({ t: 'ref', v: parseRef(w) });
            else out.push({ t: 'name', v: w.toUpperCase() });
            continue;
        }
        if ((m = /^(<=|>=|<>|[=<>+\-*/(),:])/.exec(src.slice(i)))) { out.push({ t: 'op', v: m[0] }); i += m[0].length; continue; }
        throw new ParseError(ch);
    }
    return out;
}

function parse(src) {
    const toks = tokenize(src);
    let i = 0;
    const peek = (v) => toks[i] && toks[i].t === 'op' && (v === undefined || toks[i].v === v);
    const eat = (v) => { if (!peek(v)) throw new ParseError(v); i++; };
    const CMP = ['=', '<>', '<', '>', '<=', '>='];
    function cmp() {
        let n = add();
        while (toks[i] && toks[i].t === 'op' && CMP.includes(toks[i].v)) { const op = toks[i++].v; n = { k: 'bin', op, a: n, b: add() }; }
        return n;
    }
    function add() {
        let n = mul();
        while (peek('+') || peek('-')) { const op = toks[i++].v; n = { k: 'bin', op, a: n, b: mul() }; }
        return n;
    }
    function mul() {
        let n = un();
        while (peek('*') || peek('/')) { const op = toks[i++].v; n = { k: 'bin', op, a: n, b: un() }; }
        return n;
    }
    function un() {
        if (peek('-')) { i++; return { k: 'neg', a: un() }; }
        return prim();
    }
    function prim() {
        const t = toks[i];
        if (!t) throw new ParseError('eof');
        if (t.t === 'num') { i++; return { k: 'num', v: t.v }; }
        if (t.t === 'ref') { i++; if (peek(':')) throw new ParseError('range'); return { k: 'ref', v: t.v }; }
        if (t.t === 'name') {
            i++; eat('(');
            const args = [];
            if (!peek(')')) {
                for (;;) { args.push(arg()); if (peek(',')) { i++; continue; } break; }
            }
            eat(')');
            if (t.v === 'IF' && args.length !== 3) throw new ParseError('if');
            return { k: 'fn', name: t.v, args };
        }
        if (peek('(')) { i++; const n = cmp(); eat(')'); return n; }
        throw new ParseError('tok');
    }
    function arg() {
        if (toks[i] && toks[i].t === 'ref' && toks[i + 1] && toks[i + 1].t === 'op' && toks[i + 1].v === ':') {
            const a = toks[i].v; i += 2;
            const b = toks[i];
            if (!b || b.t !== 'ref') throw new ParseError('range');
            i++;
            return { k: 'range', a, b: b.v };
        }
        return cmp();
    }
    const n = cmp();
    if (i !== toks.length) throw new ParseError('trailing');
    return n;
}

function collect(node, refs, ranges) {
    if (!node) return;
    if (node.k === 'ref' && node.v) refs.push(key(node.v.col, node.v.row));
    else if (node.k === 'range' && node.a && node.b) ranges.push(rect(node.a, node.b));
    else if (node.k === 'bin') { collect(node.a, refs, ranges); collect(node.b, refs, ranges); }
    else if (node.k === 'neg') collect(node.a, refs, ranges);
    else if (node.k === 'fn') for (const a of node.args) collect(a, refs, ranges);
}
const rect = (a, b) => ({ c0: Math.min(a.col, b.col), c1: Math.max(a.col, b.col), r0: Math.min(a.row, b.row), r1: Math.max(a.row, b.row) });

export class Sheet {
    constructor() { this.cells = new Map(); this.values = null; }

    set(ref, raw) {
        const k = norm(ref);
        this.values = null;
        if (raw === '') { this.cells.delete(k); return; }
        const s = String(raw);
        if (s.trim() !== '' && Number.isFinite(Number(s.trim()))) { this.cells.set(k, { num: Number(s.trim()) }); return; }
        if (s.startsWith('=')) {
            let ast = null;
            try { ast = parse(s.slice(1)); } catch (e) { if (!(e instanceof ParseError)) throw e; }
            const refs = [], ranges = [];
            collect(ast, refs, ranges);
            this.cells.set(k, { ast, refs, ranges, parseError: ast === null });
            return;
        }
        this.cells.set(k, { text: s });
    }

    get(ref) {
        const k = norm(ref);
        if (!this.values) this.recompute();
        const c = this.cells.get(k);
        if (!c) return null;
        if ('num' in c) return c.num;
        if ('text' in c) return c.text;
        const v = this.values.get(k);
        return isErr(v) ? v.err : v;
    }

    recompute() {
        const formulas = [...this.cells].filter(([, c]) => 'ast' in c);
        const fset = new Map(formulas);
        const deps = new Map();
        for (const [k, c] of formulas) {
            const d = new Set(c.refs.filter((r) => fset.has(r)));
            for (const g of c.ranges) for (const [k2] of formulas) {
                const p = parseRef(k2);
                if (p.col >= g.c0 && p.col <= g.c1 && p.row >= g.r0 && p.row <= g.r1) d.add(k2);
            }
            deps.set(k, [...d]);
        }
        // Iterative Tarjan: SCCs come out dependencies-first.
        const index = new Map(), low = new Map(), on = new Set(), stack = [], order = [], cyc = new Set();
        let n = 0;
        for (const [start] of formulas) {
            if (index.has(start)) continue;
            const work = [[start, 0]];
            index.set(start, n); low.set(start, n); n++; stack.push(start); on.add(start);
            while (work.length) {
                const top = work[work.length - 1];
                const [v, i] = top;
                const ds = deps.get(v);
                if (i < ds.length) {
                    top[1]++;
                    const w = ds[i];
                    if (!index.has(w)) { index.set(w, n); low.set(w, n); n++; stack.push(w); on.add(w); work.push([w, 0]); }
                    else if (on.has(w)) low.set(v, Math.min(low.get(v), index.get(w)));
                } else {
                    work.pop();
                    if (work.length) { const u = work[work.length - 1][0]; low.set(u, Math.min(low.get(u), low.get(v))); }
                    if (low.get(v) === index.get(v)) {
                        const comp = [];
                        let w;
                        do { w = stack.pop(); on.delete(w); comp.push(w); } while (w !== v);
                        if (comp.length > 1 || deps.get(v).includes(v)) for (const x of comp) cyc.add(x);
                        order.push(...comp);
                    }
                }
            }
        }
        const values = new Map();
        this.values = values;
        for (const k of order) {
            const c = fset.get(k);
            if (cyc.has(k)) { values.set(k, ERR('#CYCLE!')); continue; }
            if (c.parseError) { values.set(k, ERR('#PARSE!')); continue; }
            const v = this.ev(c.ast);
            values.set(k, v === EMPTY ? 0 : v);
        }
    }

    cell(k) {
        const c = this.cells.get(k);
        if (!c) return EMPTY;
        if ('num' in c) return c.num;
        if ('text' in c) return c.text;
        return this.values.get(k);
    }

    num(v) {
        if (isErr(v)) return v;
        if (v === EMPTY) return 0;
        if (typeof v === 'string') return ERR('#VALUE!');
        return v;
    }

    ev(node) {
        switch (node.k) {
            case 'num': return node.v;
            case 'ref': return node.v ? this.cell(key(node.v.col, node.v.row)) : ERR('#REF!');
            case 'neg': { const a = this.num(this.ev(node.a)); return isErr(a) ? a : -a; }
            case 'bin': {
                const a = this.num(this.ev(node.a)); if (isErr(a)) return a;
                const b = this.num(this.ev(node.b)); if (isErr(b)) return b;
                switch (node.op) {
                    case '+': return a + b;
                    case '-': return a - b;
                    case '*': return a * b;
                    case '/': return b === 0 ? ERR('#DIV/0!') : a / b;
                    case '=': return a === b ? 1 : 0;
                    case '<>': return a !== b ? 1 : 0;
                    case '<': return a < b ? 1 : 0;
                    case '>': return a > b ? 1 : 0;
                    case '<=': return a <= b ? 1 : 0;
                    case '>=': return a >= b ? 1 : 0;
                }
            }
            case 'fn': {
                if (node.name === 'IF') {
                    const c = this.num(this.ev(node.args[0])); if (isErr(c)) return c;
                    return this.ev(node.args[c !== 0 ? 1 : 2]);
                }
                if (!['SUM', 'MIN', 'MAX', 'COUNT'].includes(node.name)) return ERR('#NAME?');
                const nums = [];
                for (const a of node.args) {
                    if (a.k === 'range') {
                        if (!a.a || !a.b) return ERR('#REF!');
                        const g = rect(a.a, a.b);
                        for (let r = g.r0; r <= g.r1; r++) for (let c = g.c0; c <= g.c1; c++) {
                            const v = this.cell(key(c, r));
                            if (isErr(v)) return v;
                            if (typeof v === 'number') nums.push(v);
                        }
                    } else {
                        const v = this.ev(a);
                        if (isErr(v)) return v;
                        if (typeof v === 'number') nums.push(v);
                    }
                }
                if (node.name === 'SUM') return nums.reduce((s, x) => s + x, 0);
                if (node.name === 'COUNT') return nums.length;
                if (!nums.length) return 0;
                return node.name === 'MIN' ? Math.min(...nums) : Math.max(...nums);
            }
        }
        return ERR('#PARSE!');
    }
}
