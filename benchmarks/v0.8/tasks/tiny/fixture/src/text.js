export function truncate(text, max) {
  if (typeof text !== 'string') throw new TypeError('truncate expects a string');
  if (!Number.isInteger(max) || max < 1) throw new RangeError('max must be a positive integer');
  return text.length <= max ? text : text.slice(0, max - 1) + '…';
}

export function wordCount(text) {
  if (typeof text !== 'string') throw new TypeError('wordCount expects a string');
  const words = text.trim().split(/\s+/);
  return words[0] === '' ? 0 : words.length;
}
