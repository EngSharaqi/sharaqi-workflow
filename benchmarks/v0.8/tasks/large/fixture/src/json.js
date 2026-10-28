import { createEvent } from './event.js';

// One JSON object per line: {"id","type","userId","at","data"}.
export function toJsonLines(events) {
  return events.map((e) => JSON.stringify({ id: e.id, type: e.type, userId: e.userId, at: e.at, data: e.data })).join('\n') + '\n';
}

export function parseJsonLines(text) {
  return text.split('\n').filter((l) => l.trim() !== '').map((line, i) => {
    let obj;
    try {
      obj = JSON.parse(line);
    } catch {
      throw new Error(`line ${i + 1}: not valid JSON`);
    }
    try {
      return createEvent({ id: obj.id, type: obj.type, userId: obj.userId, at: obj.at, data: obj.data ?? {} });
    } catch (e) {
      throw new Error(`line ${i + 1}: ${e.message}`);
    }
  });
}
