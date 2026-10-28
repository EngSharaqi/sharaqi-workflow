export function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim() !== '';
}

export function isPositiveInteger(value) {
  return Number.isInteger(value) && value > 0;
}

export function roundTo(value, decimals) {
  const f = 10 ** decimals;
  return Math.round(value * f) / f;
}
