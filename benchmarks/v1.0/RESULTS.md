# Three-arm routing benchmark: results, 2026-10-28

One paid round (`REPS=1`) of the kit in [MANIFEST.md](MANIFEST.md): 11 routing cases ×
3 arms, 33 `claude -p` calls, interleaved with rotating arm order. All 33 completed; none
missing, none failed, every cost known. Raw records, the scorer's output and the run log:
[results-2026-10-28/](results-2026-10-28/).

- Claude Code 2.1.312; `--model opus --effort medium` in every arm.
- v0.9: `git archive a05e49d` (commit `a05e49d32918b5716066f573db7df11fa6c45c1c`).
- v1.0: `worktree-tree:c5d2f5f132e5456d2ee9331c47ecf3d396e2c4cc` (`prepare.sh`).
- Preflight 33/33 against the local stand-in API before the paid run.
- `CAP_USD=12`; total spend **$5.6351**, never near the cap.

## Overall

| | Plain Claude Code | Sharaqi v0.9 | Sharaqi v1.0 |
|---|---:|---:|---:|
| Runs completed | 11/11 | 11/11 | 11/11 |
| Cost, 11 cases (CLI `total_cost_usd`) | $2.0351 | $2.6817 | **$0.9183** |
| Median cost per case | $0.1857 | $0.2405 | **$0.0678** |
| Wall clock, sum · median | 194.2 s · 16.0 s | 168.4 s · 13.0 s | **123.4 s · 10.2 s** |
| CLI time (`duration_ms`), sum · median | 168.5 s · 13.6 s | 141.5 s · 9.9 s | **97.1 s · 7.9 s** |
| Turns | 37 | 25 | 14 |
| Routes as expected | not exposed | 11/11 | 11/11 |
| Route-format issues | — | 7 (trailing backtick) | 0 |
| Opus escalations | — (Opus seat) | — (Opus seat) | 0 |
| Cost vs Plain | — | +31.8% | **−54.9%** |
| Wall clock vs Plain (sum) | — | −13.3% | **−36.5%** |
| CLI time vs Plain (sum) | — | −16.0% | −42.4% |

Wall clock is the time around each process (`Time::HiRes`), summed per arm. The whole
interleaved round took 493 s (15:22:29–15:30:42 UTC); it can't be split per arm.

Transcript estimates (`prices.json`), never added to the CLI figure: Plain $2.0337, v0.9
$2.6817, v1.0 $0.9562 (Sonnet estimates run ~$0.0025 per run above the CLI cost).

## Per case

| Case | Plain $ | v0.9 $ | v1.0 $ | Plain s | v0.9 s | v1.0 s | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 0.1962 | 0.2400 | 0.1672 | 21.8 | 10.8 | 11.2 | v1.0 cold cache (0 read, 41k written); Plain warm |
| 2 | 0.1909 | 0.2423 | 0.0638 | 16.0 | 16.0 | 11.8 | |
| 3 | 0.1853 | 0.2412 | 0.0656 | 13.8 | 10.6 | 7.1 | |
| 4 | 0.1759 | 0.2368 | 0.0638 | 14.6 | 12.0 | 6.2 | critical; stops for approval, so no Opus reviewer ran |
| 5 | 0.1909 | 0.2405 | 0.0667 | 22.4 | 14.8 | 5.3 | |
| 6 | 0.1803 | 0.2392 | 0.0619 | 14.0 | 10.8 | 5.3 | |
| 7a | 0.1718 | 0.2563 | 0.1231 | 16.0 | 23.4 | 30.9 | v1.0 ran its Sonnet reviewer |
| 7b | 0.1677 | 0.2905 | 0.0987 | 7.9 | 24.2 | 17.1 | v0.9's Opus reviewer blocked by its own context gate |
| 8 | 0.1976 | 0.2454 | 0.0693 | 35.2 | 21.7 | 11.5 | |
| 9 | 0.1926 | 0.2402 | 0.0678 | 15.3 | 13.0 | 6.8 | critical; as case 4 |
| 10 | 0.1857 | 0.2093 | 0.0703 | 17.2 | 11.1 | 10.2 | |

## Against the published v0.9 and Plain runs

| | Published | This round | Δ |
|---|---:|---:|---:|
| Plain total | $2.0657 | $2.0351 | −1.5% |
| Plain median | $0.1873 | $0.1857 | −0.9% |
| v0.9 total | $2.9817 | $2.6817 | −10.1% |
| v0.9, cases 2–10 | $2.5356 | $2.4417 | −3.7% |

Plain reproduces within 2%. Most of v0.9's drop is case 1, cold in the published run
($0.4461) and warm here ($0.2400). Plain's time rose (CLI 136.1 s → 168.5 s) despite
stdin from `/dev/null`; the cause was not investigated.

## What this does and doesn't show

- **Shows:** on these 11 routing decisions, v1.0 reached the same routes as v0.9 at 55%
  less cost than plain Claude Code and 66% less than v0.9, and answered faster.
- **Where the saving comes from:** the session runs on Sonnet instead of Opus, the skill
  text is 1.7 KB instead of 18.5 KB, and routing happens in a hook before the first model
  turn (14 turns over 11 cases, against 25 for v0.9 and 37 for Plain).
- **Doesn't show:** task completion, code quality or end-to-end time. No file could be
  edited, no plan was approved, and the two CRITICAL cases stopped before their Opus
  review, so the Opus cost of real critical work is not in these numbers.
- **Limits:** one run per arm and case (no variance); v1.0's classifier was written with
  these 11 cases visible, so 11/11 is weak evidence for new prompts; case 1 was cold for
  v1.0 and warm for Plain, which counts against v1.0.
- **Next:** an end-to-end task benchmark with editing, approval, CRITICAL reviews and
  `REPS ≥ 3`.
