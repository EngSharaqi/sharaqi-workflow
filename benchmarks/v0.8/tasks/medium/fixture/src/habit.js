import { parseDay } from './util.js';

const MAX_NAME = 60;

export function createHabit({ name, createdOn } = {}) {
  if (typeof name !== 'string' || name.trim() === '') {
    throw new Error('habit name is required');
  }
  if (name.length > MAX_NAME) throw new Error(`habit name is longer than ${MAX_NAME} characters`);
  parseDay(createdOn);
  return { name: name.trim(), createdOn };
}
