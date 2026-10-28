// Durations written as unit groups, largest first: "1h30m", "45m", "2h".
const UNIT_SECONDS = { h: 3600, m: 60 };
const GROUP = /(\d+)([hm])/g;

// Returns the duration in seconds.
export function parseDuration(text) {
  if (typeof text !== 'string') throw new TypeError('parseDuration expects a string');
  const s = text.trim();
  if (s === '') throw new Error('empty duration');
  let total = 0;
  let consumed = 0;
  for (const g of s.matchAll(GROUP)) {
    if (g.index !== consumed) throw new Error(`invalid duration: ${text}`);
    total += Number(g[1]) * UNIT_SECONDS[g[2]];
    consumed = g.index + g[0].length;
  }
  if (consumed !== s.length) throw new Error(`invalid duration: ${text}`);
  return total;
}

export { UNIT_SECONDS };
