# Routing — which agent, model and effort for a card

The planner fills `agent`, `model` and `effort` on every card from this file and
writes a one-line reason. Pick the **lowest row that can do the card without
making a decision the card did not make for it**. If a card needs a judgement
call, the card is not finished — make the call in the card, then route it.

Ceiling: `opus` at `high`. `fable`, `xhigh` and `max` are not allowed anywhere.
**Sonnet is never above `medium`.** A builder is never above `opus/medium`.

## Matrix

| # | Card looks like | Agent | Model / effort |
|---|---|---|---|
| 1 | Run commands and report: `npm install`, `composer install`, `php artisan migrate --pretend`, run tests, `git status` / `diff` / `log`, clear caches | `runner` | haiku / low |
| 2 | Mechanical edit with the **exact text given**: rename, move a file, add translation keys, apply a before/after block, bump a version, fix lint by rule | `runner` | haiku / low |
| 3 | Same as 2 but across 4+ files, or with a check that must not be skipped (search for all usages first, run verify) | `runner` | haiku / medium |
| 4 | Boilerplate from a pattern that exists in the repo: new migration, model, form request, route, blade view copied from a named sibling | `builder` | haiku / medium |
| 4b | Small code change fully given in the card (before/after for every hunk) but needing a judgement-free read of 1–2 files to place it | `builder` | sonnet / low |
| 5 | Standard implementation from a complete card: controller method, service logic, query, component, test cases listed in the card | `builder` | sonnet / medium |
| 6 | Longer or tricky card: multi-file change with ordering, non-trivial query or state logic, debugging with a stated hypothesis, edge-case tests; or a card that failed at row 5 | `builder` | opus / medium |
| — | Planning, card amendments | `planner` | opus / medium or high — chosen by the dispatcher from task clarity |
| — | Review | `reviewer` | opus / medium by default; opus / high only for a large, risky or intricate diff — chosen by the dispatcher. Every run that changes a file is reviewed |

Prefer splitting a row-6 card into row-5 cards when the parts are separable:
two Sonnet cards are cheaper than one Opus card.

## Why these rows (Anthropic guidance, checked 2026-10-22)

- Haiku 5.5: Anthropic positions it for high-volume work and subagent tasks.
  `low` suits "short tool tasks"; at `low` it is "more likely to skip a search,
  stop early, or skip a check" in long prompts — so row 3 uses `medium`, and
  runner cards stay short.
- Sonnet 5.5: for agentic coding, "start with `medium` for well-specified tasks
  and move to `high` for harder or longer ones". A sharaqi card is well specified by
  construction, so `medium` is its ceiling here; a card that would need Sonnet
  `high` goes to Opus `medium` instead (Opus at medium is its own default and
  usually finishes a hard card in fewer turns).
- Opus 5.5: default effort is `medium`; `high` is a step above default, kept for
  planning an unclear task and reviewing a large or risky diff.
- Prices per million tokens (input/output): Opus 5.5 $4/$20, Sonnet 5.5 $2/$10,
  Haiku 5.5 from $0.10/$0.50. Opus→Sonnet halves the price; anything that can
  go to Haiku is an order of magnitude cheaper. Effort moves cost inside a model
  as much as switching models does.

## Haiku and 100K

Haiku 5.5 is priced per request: up to 100K tokens of prompt it is $0.10 in /
$0.50 out; above that every token of that request costs 5× ($0.50 / $2.50).
Even then it is ~4× cheaper than Sonnet ($2 / $10), so **a Haiku card that
grows past 100K is split, not upgraded**:

- ≤ ~3 context files or line ranges per Haiku card; no whole file over ~300 lines.
- Command output always `| tail -40`; tests targeted.
- Runner `maxTurns` is 20, so its context cannot drift far; a card that needs
  more turns is two cards.
- The token report prints `HAIKU_OVER_100K`; any agent listed there gets
  smaller cards next time.

## Splitting rules

- One card = one agent run that ends in a verifiable state. If a card needs both
  "run commands" and "write logic", split it: runner card + builder card.
- A card touches at most ~5 files. More → split by layer or by feature slice.
- Cards that touch the same file go in sequence, never the same wave.
- `git commit` / `push` / PR cards are written but marked `needs_user_ok: true`.
  The dispatcher will not run them without the user's yes.

## When NOT to delegate

Do not split work into cards when the whole task is one dependent chain that fits
in a single short context (e.g. a small bug where finding the cause *is* the fix).
Write one card at row 6 instead. Delegation saves tokens on routine bulk
work, not on tightly coupled reasoning.
