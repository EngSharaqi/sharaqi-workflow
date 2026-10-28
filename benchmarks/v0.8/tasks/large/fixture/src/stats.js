import { countBy } from './group.js';

// Mean number of events per distinct user, rounded to two decimals; null for no events.
export function eventsPerUser(events) {
  if (events.length === 0) return null;
  const users = Object.keys(countBy(events, 'userId')).length;
  return Math.round((events.length / users) * 100) / 100;
}

// The day with the most events; the earliest such day on a tie; null for no events.
export function busiestDay(events) {
  const counts = countBy(events, 'day');
  let best = null;
  for (const [day, n] of Object.entries(counts)) {
    if (best === null || n > counts[best] || (n === counts[best] && day < best)) best = day;
  }
  return best;
}
