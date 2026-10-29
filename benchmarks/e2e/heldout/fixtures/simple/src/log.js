import { formatDuration } from './duration.js';

export function jobLine(name, startedAt, endedAt) {
    return `${name} finished in ${formatDuration(endedAt - startedAt)}`;
}
