Held-out tasks, written 2026-10-29 after the routing changes, so the classifier was never tuned
on them. Each code task has a reference implementation (`../reference/`, never shown to either
arm) that passes its hidden tests, and a fixture that fails them:

| task | hidden tests | fixture | reference |
|---|---:|---:|---:|
| simple | 10 | 5 pass | 10 pass |
| medium | 11 | 1 pass | 11 pass |
| complex | 19 | 0 pass | 19 pass |
| research | `hidden/research/rubric.json` (coverage only) + link check | — | — |
