import { createHabit } from './habit.js';

export const CSV_HEADER = 'name,createdOn';

const cell = (v) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);

export function toCsv(habits) {
  const rows = habits.map((h) => [h.name, h.createdOn].map(cell).join(','));
  return [CSV_HEADER, ...rows].join('\n') + '\n';
}

function splitRow(line) {
  const out = [];
  let cur = '';
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (quoted) {
      if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (c === '"') quoted = false;
      else cur += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { out.push(cur); cur = ''; }
    else cur += c;
  }
  out.push(cur);
  return out;
}

export function parseCsv(text) {
  const lines = text.split('\n').filter((l) => l.trim() !== '');
  if (lines[0] !== CSV_HEADER) throw new Error(`expected header: ${CSV_HEADER}`);
  return lines.slice(1).map((line, i) => {
    const [name, createdOn] = splitRow(line);
    try {
      return createHabit({ name, createdOn });
    } catch (e) {
      throw new Error(`row ${i + 2}: ${e.message}`);
    }
  });
}
