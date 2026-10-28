# Contributing

Issues and pull requests are welcome. Keep changes small and say what they fix.

## Run the tests

```bash
bash tests/test_hooks.sh
python3 -m unittest discover -s tests
```

Both run offline and need only bash and Python 3 (jq is optional; the hook
tests cover every parser that's installed). CI runs them on Ubuntu and macOS.

## Rules for changes

- **Token economy.** `SKILL.md` is loaded on every run. A change to it should
  be net-neutral in bytes or smaller; say the before and after size
  (`wc -c SKILL.md`) in the PR. Detail belongs in `references/`, which is read
  only when needed.
- **No tuning to one benchmark.** A change must make sense for any repo.
  If an idea only helps the benchmark task, write it down as rejected.
- **Evidence for claims.** A number in the README or CHANGELOG needs a file
  in `benchmarks/` or a test behind it.
- **Prices.** A new row in `scripts/prices.json` is `"verified": false` until
  it reproduces Claude Code's own `costUSD` on a recorded session.

## Run a benchmark

`benchmarks/medium-task/` holds a pre-registered protocol, a fixture, hidden
tests, an edge probe and the harness (`run.sh`). It needs the `claude` CLI
and spends real money: read `PROTOCOL.md` first. To measure on your own repo,
fill in [benchmarks/TEMPLATE.md](benchmarks/TEMPLATE.md).
