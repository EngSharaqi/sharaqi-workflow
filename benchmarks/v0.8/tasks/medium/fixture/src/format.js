const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

// "Read — streak 3 days"
export function formatHabit(habit, streak) {
  return `${habit.name} — streak ${plural(streak, 'day')}`;
}
