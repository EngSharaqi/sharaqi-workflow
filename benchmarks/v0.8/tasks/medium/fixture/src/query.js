const SORT_KEYS = ['name', 'createdOn'];

export function filterHabits(habits, { nameContains, createdAfter } = {}) {
  return habits.filter((h) => {
    if (nameContains !== undefined && !h.name.toLowerCase().includes(nameContains.toLowerCase())) {
      return false;
    }
    if (createdAfter !== undefined && !(h.createdOn > createdAfter)) return false;
    return true;
  });
}

export function sortHabits(habits, key = 'name', direction = 'asc') {
  if (!SORT_KEYS.includes(key)) throw new Error(`unknown sort key: ${key}`);
  const sign = direction === 'desc' ? -1 : 1;
  return [...habits].sort((a, b) => (a[key] < b[key] ? -sign : a[key] > b[key] ? sign : 0));
}
