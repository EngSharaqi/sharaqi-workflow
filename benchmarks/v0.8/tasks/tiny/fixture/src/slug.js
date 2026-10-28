// URL slugs: lower case, ASCII letters and digits, words joined by single hyphens.
export function slugify(text) {
  if (typeof text !== 'string') throw new TypeError('slugify expects a string');
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '-');
}
