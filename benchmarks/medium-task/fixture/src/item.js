import { isNonEmptyString, isPositiveInteger } from './util.js';

// Validates raw input and returns a normalised item. Throws on invalid input.
export function createItem(input) {
  if (input === null || typeof input !== 'object') {
    throw new TypeError('item must be an object');
  }
  const { title, author, pages, year } = input;
  if (!isNonEmptyString(title)) {
    throw new TypeError('title must be a non-empty string');
  }
  if (!isNonEmptyString(author)) {
    throw new TypeError('author must be a non-empty string');
  }
  if (!isPositiveInteger(pages)) {
    throw new RangeError('pages must be a positive integer');
  }
  if (year !== undefined && year !== null && !Number.isInteger(year)) {
    throw new TypeError('year must be an integer');
  }
  return {
    title: title.trim(),
    author: author.trim(),
    pages,
    year: year ?? null,
  };
}
