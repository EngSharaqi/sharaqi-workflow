# Routing cases: results — 2026-10-25

Cases and scoring: [routing-cases.md](routing-cases.md), pre-registered and
unchanged (`shasum -a 256 -c HASHES.sha256` passes). One run per case,
`/sharaqi:sharaqi route <task>` via [route.sh](route.sh), Claude Code
2.1.274, `--model opus --effort medium` (resolved to `claude-opus-5`), the
v0.8.0 plugin from one frozen snapshot.

## Result

**15 of 16 cases match** (executor in the acceptable set and plan in the plan
set). Secondary: plan 16/16, review 16/16, mode 15/16.

Every run took one turn and made no tool call (the PreToolUse log of each run
is empty). Cost: $3.75 for the 16 runs; $0.19–0.20 per run with a warm
prompt cache, $0.40–0.41 for the three that started cold.

| Case | Shape | Expected: plan · executor | Card | Match |
|---|---|---|---|---|
| R1 | tiny known edit | none · inline | FAST · none · inline · self | yes |
| R2 | clear small bug, tests | none · inline/haiku/sonnet-low | FAST · none · inline · self | yes |
| R3 | mechanical rename, 10 files | none · haiku/sonnet-low | FAST · none · haiku · self | yes |
| R4 | boilerplate on a pattern | none · haiku/sonnet-low | STANDARD · none · haiku · self | yes (mode miss) |
| R5 | translations, small | none · inline/haiku | FAST · none · **sonnet-low** · self | **no** |
| R6 | medium feature, clear spec | none/chat · sonnet-low/medium | STANDARD · none · sonnet-medium · reviewer-sonnet | yes |
| R7 | medium feature, input parsing | none · inline/sonnet-low/medium | STANDARD · none · sonnet-low · reviewer-sonnet | yes |
| R8 | ambiguous request | chat · ask/sonnet-medium/high/opus-medium | STANDARD · chat · sonnet-medium · reviewer-sonnet | yes |
| R9 | perf investigation | none/chat · inline/ask/sonnet-high/opus-medium | STANDARD · chat · sonnet-high · reviewer-sonnet | yes |
| R10 | race across 3 files | chat/plan-agent · sonnet-high/opus-medium/high | STANDARD · chat · sonnet-high · reviewer-sonnet | yes |
| R11 | no-test legacy code | none · inline/sonnet-low/medium | STANDARD · none · sonnet-medium · reviewer-sonnet | yes |
| R12 | auth change, tiny | chat/plan-agent · inline/sonnet-low | CRITICAL · chat · inline · reviewer-opus | yes |
| R13 | data migration | chat/plan-agent · inline/sonnet-medium/high/opus-medium | CRITICAL · chat · sonnet-high · reviewer-opus | yes |
| R14 | CI config, tiny | chat/plan-agent · inline | CRITICAL · chat · inline · reviewer-opus | yes |
| R15 | upload parsing | chat/plan-agent · sonnet-medium/high/opus-medium | CRITICAL · chat · sonnet-medium · reviewer-opus | yes |
| R16 | moment → date-fns, 14 files | chat/plan-agent · sonnet-low/medium | CRITICAL · chat · sonnet-medium ×2 parallel · reviewer-opus | yes |

## Misses, with the reason

- **R5 (executor).** The router chose `sonnet-low` for 25 Arabic
  translations: "Arabic wording needs more judgement than haiku". The label
  accepted `inline` or `haiku`. The router's reasoning is defensible on
  quality grounds; on cost, 25 short strings are about the size the
  break-even keeps inline. Counted as a miss; the label is not changed.
- **R4 (mode, secondary).** STANDARD instead of FAST for new Storybook
  stories. The executor and review matched; only the mode was one step more
  cautious than the label, which the skill's "unsure FAST/STANDARD →
  STANDARD" rule allows.

## Observations

- Reasons cite the inputs the skill names: size, whether tests exist (R6,
  R7: "tests present → one rung down"; R11: "no check … one rung up"), the
  CRITICAL trigger, and the review trigger by risk.
- R8 printed one extra line after the card ("Route only — nothing was read
  or run …"). The card itself was within three lines in all 16 runs.
- R16 split the work into two parallel slices on disjoint files, as the
  slice rule asks.
- Not measured here: whether the chosen rung then gets the work right. That
  is what the end-to-end benchmark measures.

## Raw cards

The `result` text of each run, verbatim except for code fences removed.

**R1**

```
FAST | Plan: none | Executor: inline | Review: self
Why: one-word label typo in a single named file, no logic or callers affected — a read and an edit, narrowest relevant check suffices.
```

**R2**

```
FAST | Plan: none | Executor: inline | Review: self
Why: one-line off-by-one in a named file plus one December test — two edits, covered by an existing suite (npm test) as the narrowest check, no callers or data at risk.
```

**R3**

```
FAST | Plan: none | Executor: haiku | Review: self
Why: compiler-checked mechanical rename, ~40 occurrences on one pattern, typecheck + tests green today catch any missed call site; no behaviour change.
```

**R4**

```
STANDARD | Plan: none | Executor: haiku | Review: self
Why: 8 new story files, mechanical on the Button.stories.jsx pattern already in the repo; no product code touched so no behaviour to break; checks are the repo's lint/Storybook build, review self since nothing with callers or validation changes.
```

**R5**

```
FAST | Plan: none | Executor: sonnet-low | Review: self
Why: 25 string additions to one JSON file, pattern already in the file; Arabic wording needs more judgement than haiku, no behaviour change, no callers — narrowest check is valid JSON + key parity with en.json.
```

**R6**

```
STANDARD | Plan: none | Executor: sonnet-medium | Review: reviewer-sonnet
Why: six named files plus tests for one clear optional field — `npm test` is the check, so a rung below instinct; it touches validation and a query filter, so an independent reviewer is due.
```

**R7**

```
STANDARD | Plan: none | Executor: sonnet-low | Review: reviewer-sonnet
Why: small clear two-file feature with jest tests to prove it (tests present → one rung down); risk is query-param validation (pageSize default/max, bad input), so an independent reviewer.
```

**R8**

```
STANDARD | Plan: chat | Executor: sonnet-medium | Review: reviewer-sonnet
Why: normal feature work on a hot path; chat plan because the ask names no cache layer, key, TTL or invalidation rule; reviewer-sonnet because caching changes behaviour for every caller of the product API and stale/incorrectly-keyed entries won't show up in existing tests.

Route only — nothing was read or run. Say `do Add caching to the product API, it's too slow.` to execute.
```

**R9**

```
STANDARD | Plan: chat | Executor: sonnet-high | Review: reviewer-sonnet
Why: unknown-cause regression — diagnosis spans the route's queries/data layer before any edit, so a ≤15-line chat plan fixes the cause before code; perf fix is unlikely to have a covering test and the loader probably has several callers, hence an independent reviewer.
```

**R10**

```
STANDARD | Plan: chat | Executor: sonnet-high | Review: reviewer-sonnet
Why: three interacting files and an ambiguous fix design (atomic conditional update vs transaction/lock) → short chat plan; a failing repro test bounds the work, so sonnet-high implements; concurrency correctness across shared reservation paths warrants an independent reviewer.
```

**R11**

```
STANDARD | Plan: none | Executor: sonnet-medium | Review: reviewer-sonnet
Why: small, clearly-specified delimiter+quoting change, but a 1,200-line legacy file with zero tests in the repo means no check can confirm it — so one rung up from sonnet-low, and an independent reviewer since export behaviour changes with nothing covering it.
```

**R12**

```
CRITICAL | Plan: chat | Executor: inline | Review: reviewer-opus
Why: one-line middleware add on a pattern the file already shows, with tests covering the routes — but it's a permissions check on a destructive route, so CRITICAL: chat plan for the negative cases, reviewer-opus mandatory.
```

**R13**

```
CRITICAL | Plan: chat | Executor: sonnet-high | Review: reviewer-opus
Why: data migration rewriting existing rows in Postgres with a lossy, non-trivial down path — name splitting has messy edge inputs (single token, empty/NULL, multi-part surnames, extra whitespace) and migrations aren't covered by tests here, so a chat plan is required by CRITICAL and reviewer-opus is mandatory.
```

**R14**

```
CRITICAL | Plan: chat | Executor: inline | Review: reviewer-opus
Why: one-line matrix edit in .github/workflows/ci.yml, but CI config is a CRITICAL trigger — chat plan because CRITICAL, reviewer-opus mandatory there; inline since it's a single known edit I can't verify by running CI here.
```

**R15**

```
CRITICAL | Plan: chat | Executor: sonnet-medium | Review: reviewer-opus
Why: one new route + tests, but an uploaded-file parser with a 5 MB cap and per-row email validation is security-sensitive parsing — chat plan to pin the limit/partial-failure behaviour, reviewer-opus because CRITICAL.
```

**R16**

```
CRITICAL | Plan: chat | Executor: sonnet-medium ×2 parallel | Review: reviewer-opus
Why: 14 files + a dependency removal (CRITICAL trigger: dependencies); npm test covers the formatting so a rung below instinct, split into two disjoint file slices; chat plan because moment→date-fns token mapping must be agreed before editing, and reviewer-opus is mandatory in CRITICAL.
```
