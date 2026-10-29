// Human-readable durations for the job runner's log lines: "1h 2m 3s", "4m 5s", "6s".
// Hours and minutes are left out while they are zero at the front; seconds are always shown.
export function formatDuration(ms) {
    if (!Number.isFinite(ms) || ms < 0) {
        throw new RangeError(`formatDuration: expected a non-negative number, got ${ms}`);
    }
    const totalSec = ms / 1000;
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = Math.round(totalSec % 60);
    const parts = [];
    if (h) parts.push(`${h}h`);
    if (h || m) parts.push(`${m}m`);
    parts.push(`${s}s`);
    return parts.join(' ');
}
