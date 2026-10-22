---
id: T01
title: <imperative, ≤ 8 words>
agent: builder            # runner | builder
model: sonnet                   # haiku | sonnet | opus
effort: medium                  # low | medium (sonnet max medium; opus builders medium only)
routing_reason: <one line: matrix row # and why>
browser: none                   # none | needed — <why nothing else can verify it>
depends_on: []                  # card ids
files: [app/Http/Controllers/FooController.php]   # the ONLY files this card may change
prd_refs: [5.2, AC-3]           # PRD sections the builder must read
needs_user_ok: false            # true for commit / push / PR / anything external
---

## Context (read these, nothing else)
- `path/to/file.php:120-168` — what it is and why it matters
- `path/to/sibling.php` — the pattern to copy

## Changes
For each file, in order. Give an anchor the builder can find with a search, then
the exact change. Paste code when the logic matters; describe in prose only what
is truly mechanical.

### 1. `path/to/file.php`
Anchor: method `store()` (search `public function store(`)
Replace:
```php
// exact before
```
With:
```php
// exact after
```

## Do not
- Change any file not in `files`.
- Rename, reformat or "clean up" code outside the anchors.
- Add dependencies, migrations or config unless listed above.
- <card-specific traps>

## Token limits
- Read only the files and line ranges under Context; no searching in `vendor/`,
  `node_modules/`, `storage/`, build output, lockfiles or `*.min.*`.
- Every command: `<cmd> 2>&1 | tail -40`.
- Haiku card: the whole run stays under ~100K tokens of context (Context list
  ≤ ~3 files or ranges, no file read whole if it is over ~300 lines).

## Verify
Run, in order, and expect. Targeted and fail-fast — e.g.
`php artisan test --filter=FooTest --stop-on-failure 2>&1 | tail -40`,
`npx vitest run path/to/foo.test.ts --bail=1 2>&1 | tail -40` — never the whole
suite unless the plan says why.
1. `<command>` → `<expected output or exit 0>`
2. `<command>` → `<expected>`

## Stop and report MISMATCH if
- An anchor is not found, or the "before" code differs from what is in the file.
- A verify step fails for a reason the card does not explain.
- Doing the card would require touching a file not in `files`.

## Report (return exactly this, nothing more)
```
STATUS: DONE | MISMATCH | FAILED | BLOCKED
CARD: T01
FILES: <changed files>
VERIFY: <each command → pass/fail, one line each>
NOTE: <≤ 3 lines: mismatch evidence, failure output tail, or question>
```
