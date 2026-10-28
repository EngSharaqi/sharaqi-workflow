// "2026-01-05T10:00:00Z user=alice login"
export function formatEvent(e) {
  return `${e.at} user=${e.userId} ${e.type}`;
}

export function formatEvents(events) {
  return events.map(formatEvent).join('\n');
}
