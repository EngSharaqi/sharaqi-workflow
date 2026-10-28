// filterItems(items, { author, minPages, maxPages, year }): every given option must match.
export function filterItems(items, options = {}) {
  const { author, minPages, maxPages, year } = options;
  return items.filter((item) => {
    if (author !== undefined && item.author.toLowerCase() !== author.toLowerCase()) return false;
    if (minPages !== undefined && item.pages < minPages) return false;
    if (maxPages !== undefined && item.pages > maxPages) return false;
    if (year !== undefined && item.year !== year) return false;
    return true;
  });
}

const SORT_KEYS = ['title', 'author', 'pages', 'year'];

// sortItems(items, key, direction): a new array; direction is 'asc' (default) or 'desc'.
export function sortItems(items, key = 'title', direction = 'asc') {
  if (!SORT_KEYS.includes(key)) {
    throw new RangeError(`unknown sort key: ${key}`);
  }
  if (direction !== 'asc' && direction !== 'desc') {
    throw new RangeError(`unknown sort direction: ${direction}`);
  }
  const sign = direction === 'asc' ? 1 : -1;
  return [...items].sort((a, b) => {
    const x = a[key];
    const y = b[key];
    if (typeof x === 'string') return sign * x.localeCompare(y);
    return sign * (x - y);
  });
}
