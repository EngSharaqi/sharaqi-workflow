import { createEvent } from './event.js';

// Event data is not exported to CSV.
export const CSV_HEADER = 'id,type,userId,at';

const cell = (v) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);

export function toCsv(events) {
  const rows = events.map((e) => [e.id, e.type, e.userId, e.at].map(cell).join(','));
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
    const [id, type, userId, at] = splitRow(line);
    try {
      return createEvent({ id, type, userId, at });
    } catch (e) {
      throw new Error(`row ${i + 2}: ${e.message}`);
    }
  });
}
