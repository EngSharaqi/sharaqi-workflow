# auditlog

A small audit-event library. `npm test` runs the tests (Node 20+, no dependencies).

| File | Role |
|---|---|
| `src/event.js` | create and validate an event |
| `src/store.js` | append-only store, ordered reads |
| `src/filter.js` | filter by type, user, time range |
| `src/group.js` | counts by a key |
| `src/stats.js` | per-user averages, busiest day |
| `src/format.js` | one-line text per event |
| `src/csv.js`, `src/json.js` | CSV and JSON-lines import and export |
| `src/timeline.js` | per-user timeline and sessions |
| `src/retention.js` | drop old events |
| `src/util.js` | timestamp helpers |
