// Reference resolver for the hidden tests (not shown to either arm).
const VER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;

function parseVersion(v) {
    const m = VER.exec(v);
    if (!m) throw new TypeError(`invalid version: ${v}`);
    return [+m[1], +m[2], +m[3]];
}

function cmp(a, b) {
    for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] - b[i];
    return 0;
}

const cache = new Map();

export function parseRange(range) {
    if (cache.has(range)) return cache.get(range);
    const bad = () => new TypeError(`invalid range: "${range}"`);
    if (typeof range !== 'string') throw bad();
    const alts = range.split('||').map((s) => s.trim());
    if (alts.some((a) => a === '')) throw bad();
    const parsed = alts.map((alt) => {
        if (alt === '*') return [];
        return alt.split(/\s+/).flatMap((c) => {
            const m = /^(\^|~|>=|<=|>|<|=)?(.*)$/.exec(c);
            const op = m[1] ?? '=';
            if (!VER.test(m[2])) throw bad();
            const v = parseVersion(m[2]);
            if (op === '^') {
                const hi = v[0] > 0 ? [v[0] + 1, 0, 0] : v[1] > 0 ? [0, v[1] + 1, 0] : [0, 0, v[2] + 1];
                return [['>=', v], ['<', hi]];
            }
            if (op === '~') return [['>=', v], ['<', [v[0], v[1] + 1, 0]]];
            return [[op, v]];
        });
    });
    cache.set(range, parsed);
    return parsed;
}

function satisfies(version, range) {
    const v = parseVersion(version);
    return parseRange(range).some((alt) =>
        alt.every(([op, w]) => {
            const c = cmp(v, w);
            return op === '=' ? c === 0 : op === '>' ? c > 0 : op === '>=' ? c >= 0 : op === '<' ? c < 0 : c <= 0;
        }),
    );
}

export function resolve(registry, root) {
    for (const r of Object.values(root)) parseRange(r);
    for (const name of Object.keys(root)) {
        if (!Object.hasOwn(registry, name)) {
            throw Object.assign(new Error(`package not found: ${name}`), { code: 'ENOTFOUND', package: name });
        }
    }
    let lastFail = Object.keys(root)[0];
    const sorted = new Map();
    const versionsOf = (name) => {
        if (!sorted.has(name)) {
            sorted.set(name, Object.keys(registry[name]).sort((a, b) => cmp(parseVersion(b), parseVersion(a))));
        }
        return sorted.get(name);
    };

    // selected: Map name→version; ranges: Map name→[range]; queue: names in first-needed order.
    function step(selected, ranges, queue, qi) {
        if (qi === queue.length) return selected;
        const name = queue[qi];
        const known = ranges.get(name) ?? [];
        for (const v of versionsOf(name)) {
            if (!known.every((r) => satisfies(v, r))) continue;
            const deps = registry[name][v] ?? {};
            for (const r of Object.values(deps)) parseRange(r);
            const depNames = Object.keys(deps);
            if (depNames.some((d) => !Object.hasOwn(registry, d))) continue;
            const sel = new Map(selected).set(name, v);
            const rg = new Map(ranges);
            let ok = true;
            for (const d of depNames) {
                rg.set(d, [...(rg.get(d) ?? []), deps[d]]);
                if (sel.has(d) && !satisfies(sel.get(d), deps[d])) {
                    ok = false;
                    break;
                }
            }
            if (!ok) continue;
            const q = [...queue];
            for (const d of depNames) if (!q.includes(d)) q.push(d);
            const out = step(sel, rg, q, qi + 1);
            if (out) return out;
        }
        lastFail = name;
        return null;
    }

    const ranges = new Map(Object.entries(root).map(([n, r]) => [n, [r]]));
    const out = step(new Map(), ranges, Object.keys(root), 0);
    if (!out) {
        throw Object.assign(new Error(`cannot resolve: no version of ${lastFail} satisfies every range`), {
            code: 'ERESOLVE',
        });
    }
    return Object.fromEntries(out);
}
