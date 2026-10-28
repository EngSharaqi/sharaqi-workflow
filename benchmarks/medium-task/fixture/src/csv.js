import { createItem } from './item.js';

export const CSV_HEADER = 'title,author,pages,year';

// Plain comma-separated values: no quoting, so fields can't contain commas.
export function parseCsv(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim() !== '');
  if (lines.length === 0) return [];
  if (lines[0].trim() !== CSV_HEADER) {
    throw new Error(`expected header "${CSV_HEADER}"`);
  }
  return lines.slice(1).map((line, i) => {
    const [title, author, pages, year] = line.split(',').map((cell) => cell.trim());
    try {
      return createItem({
        title,
        author,
        pages: Number(pages),
        year: year === '' || year === undefined ? undefined : Number(year),
      });
    } catch (err) {
      throw new Error(`line ${i + 2}: ${err.message}`);
    }
  });
}

export function toCsv(items) {
  const rows = items.map((item) =>
    [item.title, item.author, item.pages, item.year ?? ''].join(','),
  );
  return [CSV_HEADER, ...rows].join('\n') + '\n';
}
