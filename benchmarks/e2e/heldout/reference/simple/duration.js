export function formatDuration(ms) {
    if (!Number.isFinite(ms) || ms < 0) {
        throw new RangeError(`formatDuration: expected a non-negative number, got ${ms}`);
    }
    const totalSec = Math.round(ms / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    const parts = [];
    if (h) parts.push(`${h}h`);
    if (h || m) parts.push(`${m}m`);
    parts.push(`${s}s`);
    return parts.join(' ');
}
