# Benchmark: <task name> — <YYYY-MM-DD>

A protocol for a medium-sized task, where delegation has a chance to pay for
itself. Fill in only what you observed. Leave a cell empty rather than
estimate.

## Task

- Repo and commit:
- Task prompt (verbatim, identical in both arms):
- Why medium-sized: several files (≥ 4), some mechanical work (renames,
  boilerplate, tests shaped like their neighbours), at least one behaviour
  change with edge inputs.
- Expected mode under sharaqi triage, decided before the run:

## Setup

- Claude Code version (`claude --version`):
- Model and effort (same in both arms): `--model … --effort …`
- Headless command, with the full `--allowedTools` list. Allow everything the
  skill needs (Read of `references/`, `python3` for `tokens.py`, git), so
  permission blocks don't distort the run.
- How the plugin was loaded in each arm (`--plugin-dir`, `enabledPlugins`),
  and whether its hooks were active in the baseline.
- Runs per arm (≥ 3 if you can afford it; one run is a direction, not a
  result):

## Ground truth

- Cost: `total_cost_usd` and `modelUsage[*].costUSD` from
  `claude -p --output-format json`. That's Claude Code's own figure; `tokens.py`
  is checked against it, never the other way round.
- Hidden tests: written before the run, not visible to either arm; run after.
- Edge-input checks: a probe calling the changed functions with missing,
  wrong-type, NaN, negative, empty and huge inputs. Each should throw a clear
  error or return a defined value.

## Results

| Arm | Run | Cost $ (Claude Code) | Wall s | Turns | Hidden tests | Edge probe | Permission denials |
|---|---|---|---|---|---|---|---|
| plain | 1 | | | | | | |
| sharaqi | 1 | | | | | | |

Cost split for the sharaqi arm (from `modelUsage` and `tokens.py`):

| Run | Orchestrator (model) $ | Implementer (model) $ | Reviewer (model) $ | Other $ | tokens.py total $ | Δ vs Claude Code |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

Skill bytes loaded (SKILL.md plus each reference actually read):

| Run | Mode | Route | References read | Bytes |
|---|---|---|---|---|
| 1 | | | | |

Review findings that turned out real (each verified by a test or the probe):

| Run | Finding | Found by | Missed by the other arm? |
|---|---|---|---|
| | | | |

## Limits

List everything that weakens the comparison: number of runs, blocked
commands, hooks active in the baseline, model resolution (which model id ran),
anything cached between runs.

## Conclusion

One paragraph, in the direction the numbers point, including when they point
against sharaqi.
