import { roundTo } from './util.js';

export function totalPages(items) {
  return items.reduce((sum, item) => sum + item.pages, 0);
}

// Mean page count rounded to one decimal; null for an empty list.
export function averagePages(items) {
  if (items.length === 0) return null;
  return roundTo(totalPages(items) / items.length, 1);
}

export function countByAuthor(items) {
  const counts = {};
  for (const item of items) {
    counts[item.author] = (counts[item.author] ?? 0) + 1;
  }
  return counts;
}
