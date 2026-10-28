// "Title" by Author, 320 pages (1999)  — the year part is left out when unknown.
export function formatItem(item) {
  const year = item.year === null ? '' : ` (${item.year})`;
  return `"${item.title}" by ${item.author}, ${item.pages} pages${year}`;
}

export function formatList(items) {
  if (items.length === 0) return 'No items.';
  return items.map((item, i) => `${i + 1}. ${formatItem(item)}`).join('\n');
}
