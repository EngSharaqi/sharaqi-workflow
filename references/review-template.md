# Review <n> — <title>

Base: <sha> · Diff: `git diff <sha>` · Verdict: **PASS | FIX**

Reviewer: <model>/<effort> — <why this size>

## A · Spec — acceptance criteria
| AC | Met? | Evidence (`file:line`) | Note |
|---|---|---|---|
| AC-1 | yes / no / partly | | |

## Findings
One list per axis, most severe first inside each axis. Do not merge or re-rank
across axes. No style preferences the PRD or the repo's standards don't ask for.

### A · Spec
### R<n>-1 · spec · <severity: blocker | major | minor> · <title>
- Where: `file:line`
- What is wrong: <one or two sentences>
- Scenario: <input/state → wrong result>
- Fix card: F<n>01

### B · Quality
### R<n>-2 · quality · <severity> · <title>
(same fields)

### C · Security
| Check | Result |
|---|---|
| Injection (SQL / shell / path) | ok · finding R<n>-x · n/a |
| Authorization (middleware, policy, IDOR) | |
| Input validation & mass assignment | |
| Output / XSS | |
| CSRF & sessions | |
| Secrets & data exposure | |
| File upload / download | |
| Dependencies | |

### R<n>-3 · security · <severity> · <title>
- Where: `file:line`
- Attack: <who sends what → what they get>
- Fix card: F<n>0x

## Out-of-scope changes
Anything in the diff that no card asked for (revert or keep — say which).

## Not checked
What the reviewer could not verify and why (e.g. needs a running DB).
