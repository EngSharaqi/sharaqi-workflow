import { createEvent } from '../src/index.js';

let n = 0;
export const ev = (type, userId, at, extra = {}) => createEvent({ id: `e${++n}`, type, userId, at, ...extra });
